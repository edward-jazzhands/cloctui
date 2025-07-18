"""main.py - CLOCTUI - A TUI interface for CLOC
========================================================

# ~ Type Checking (Pyright and MyPy) - Strict Mode
# ~ Linting - Ruff
# ~ Formatting - Black - max 110 characters / line
"""

# python standard lib
from __future__ import annotations
from typing import TypedDict, Union, cast, Any
import subprocess
import os
import shutil
import json
from enum import Enum

# Textual imports
# from textual import getters
from textual import on, work
from textual.app import App, ComposeResult
from textual.widgets import Static, DataTable
from textual.widgets.data_table import ColumnKey, Column
from textual.screen import Screen
from textual.message import Message
from textual.containers import Horizontal, Vertical
from textual.binding import Binding
from rich.text import Text

# Local imports
from cloctui.spinner import SpinnerWidget


class CLOCException(Exception):

    def __init__(self, message: str, code: int):
        self.message = message
        self.code = code


class ClocFileStats(TypedDict):
    blank: int
    comment: int
    code: int
    language: str


class ClocSummaryStats(TypedDict):
    blank: int
    comment: int
    code: int
    nFiles: int


class ClocHeader(TypedDict):
    cloc_url: str
    cloc_version: str
    elapsed_seconds: float
    n_files: int
    n_lines: int
    files_per_second: float
    lines_per_second: float


ClocJsonResult = dict[str, Union[ClocFileStats, ClocSummaryStats, ClocHeader]]


# This class courtesey of Stefano Stone
# https://github.com/USIREVEAL/pycloc
# Modified by Edward Jazzhands (added all type hints and improved docstrings)
class CLOC:
    def __init__(self) -> None:
        self.base_command = "cloc"
        self.options: list[str] = []
        self.flags: list[str] = []
        self.arguments: list[str] = []
        self.working_directory = os.getcwd()

    def add_option(self, option: str, value: int) -> CLOC:
        """Adds an option with a value (e.g., --output file.txt).

        Args:
            option (str): The option name (e.g., --timeout).
            value (int): The value for the option (e.g., 30).
        """
        self.options.append(f"{option} {value}")
        return self

    def add_flag(self, flag: str) -> CLOC:
        """Adds a flag (e.g., --verbose, -v).

        Args:
            flag (str): The flag to add.
        """
        self.flags.append(flag)
        return self

    def add_argument(self, argument: str) -> CLOC:
        """Adds a positional argument (e.g., filename).

        Args:
            argument (str): The argument to add.
        """
        self.arguments.append(argument)
        return self

    def set_working_directory(self, path: str) -> CLOC:
        """Sets the working directory for the command.

        Args:
            path (str): The path to set as the working directory.
        """
        self.working_directory = path
        return self

    def build(self) -> str:
        """Constructs the full CLI command string.

        Returns:
            str: The complete command string.
        """
        parts = [self.base_command] + self.flags + self.options + self.arguments
        return " ".join(parts)

    def execute(self) -> str:
        """Executes the CLI command, returns raw process result or Exception.

        Returns:
            str: The output of the command.
        """
        command = self.build()
        try:
            process = subprocess.run(
                command, shell=True, check=True, stdout=subprocess.PIPE, cwd=self.working_directory
            )
            return process.stdout.decode("utf-8")
        except subprocess.CalledProcessError as error:
            match error.returncode:
                case 25:
                    message = "Failed to create tarfile of files from git or not a git repository."
                case 126:
                    message = "Permission denied. Please check the permissions of the working directory."
                case 127:
                    message = "CLOC command not found. Please install CLOC."
                case _:
                    message = "Unknown CLOC error: " + str(error)

            if error.returncode < 0 or error.returncode > 128:
                message = "CLOC command was terminated by signal " + str(-error.returncode)

            raise CLOCException(message, error.returncode)


class CLOCNotInstalledScreen(Screen[None]):
    """Screen to display when CLOC is not installed."""

    def compose(self) -> ComposeResult:
        with Vertical(id="error_container"):
            yield Static(
                "[bold red]CLOC is not installed on your system.[/bold red]\n"
                "Please install CLOC to use this application.\n"
                "Visit https://github.com/AlDanial/cloc for installation instructions."
            )

    def on_mount(self):
        self.app.exit()


class CustomDataTable(DataTable[Any]):


    class UpdateSummarySize(Message):
        def __init__(self, size: int):
            super().__init__()
            self.size = size
            "The new size for the summary row's first column."


    class SortingStatus(Enum):
        UNSORTED = 0  #     [-] unsorted
        ASCENDING = 1  #    [↑] ascending (reverse = True)
        DESCENDING = 2  #   [↓] descending (reverse = False)    

    COL_SIZES = {
        "path": 15, # dynamic column minimum
        "language": 14,
        "blank": 7,
        "comment": 9,
        "code": 7,
        "total": 7,
    }
    other_cols_total = sum(COL_SIZES.values()) - COL_SIZES["path"]

    sort_status: dict[str, SortingStatus] = {
        "path": SortingStatus.UNSORTED, 
        "language": SortingStatus.UNSORTED, 
        "blank": SortingStatus.UNSORTED, 
        "comment": SortingStatus.UNSORTED,
        "code": SortingStatus.UNSORTED,
        "total": SortingStatus.UNSORTED,
    }

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

        self.add_column("path [yellow]-[/]", width=self.COL_SIZES['path'], key="path")
        self.add_column("language [yellow]-[/]", width=self.COL_SIZES['language'], key="language")
        self.add_column("blank [yellow]-[/]", width=self.COL_SIZES['blank'], key="blank")
        self.add_column("comment [yellow]-[/]", width=self.COL_SIZES['comment'], key="comment")
        self.add_column("code [yellow]-[/]", width=self.COL_SIZES['code'], key="code")
        self.add_column("total [yellow]-[/]", width=self.COL_SIZES['total'], key="total")        

    def on_resize(self) -> None:

        # Account for padding on both sides of each column:
        total_cell_padding = (self.cell_padding*2) * len(self.columns)

        # Pretty obvious how this works I think:
        first_col_width = self.size.width - self.other_cols_total - total_cell_padding

        # Prevent column from being smaller than the chosen minimum:
        if first_col_width < self.COL_SIZES["path"]:
            first_col_width = self.COL_SIZES["path"]

        self.columns[ColumnKey("path")].width = first_col_width
        self.refresh()
        self.post_message(
            CustomDataTable.UpdateSummarySize(size=first_col_width+3)
        )

    @on(DataTable.HeaderSelected)
    def header_selected(self, event: DataTable.HeaderSelected) -> None:
              
        column = self.columns[event.column_key]
        self.sort_column(column, column.key)

    
    def sort_column(self, column: Column, column_key: ColumnKey) -> None:

        if column_key.value is None:
            raise ValueError("Tried to sort a column with no key.")
        if column_key.value not in self.sort_status:
            raise ValueError(
                f"Unknown column key: {column_key.value}. "
                "This should never happen, please report this issue."
            )

        value = column_key.value

        # if its currently unsorted, that means the user is switching columns
        # to sort. Reset all other columns to unsorted.
        if self.sort_status[value] == self.SortingStatus.UNSORTED:
            for key in self.sort_status:
                self.sort_status[key] = self.SortingStatus.UNSORTED
                col_index = self.get_column_index(key)
                col = self.ordered_columns[col_index]
                col.label = Text.from_markup(f"{key} [yellow]-[/]")

            # Now set chosen column to ascending:
            self.sort_status[value] = self.SortingStatus.ASCENDING
            self.sort(column_key, reverse=True)
            column.label = Text.from_markup(f"{value} [yellow]↑[/]")

        # For the other two conditions, we just toggle ascending/descending
        elif self.sort_status[value] == self.SortingStatus.ASCENDING:
            self.sort_status[value] = self.SortingStatus.DESCENDING
            self.sort(value, reverse=False)
            column.label = Text.from_markup(f"{value} [yellow]↓[/]")
        elif self.sort_status[value] == self.SortingStatus.DESCENDING:
            self.sort_status[value] = self.SortingStatus.ASCENDING
            self.sort(column_key, reverse=True)
            column.label = Text.from_markup(f"{value} [yellow]↑[/]")
        else:
            raise ValueError(
                f"Sort status for {value} is '{self.sort_status[value]}' "
                "did not meet any expected values."
            )
        
    @work(description="Updating table with CLOC data")
    async def update_table(self, file_data: dict[str, ClocFileStats]) -> None:

        for key, data in file_data.items():
            self.add_row(
                key,
                data["language"],
                data["blank"],
                data["comment"],
                data["code"],
                data["blank"] + data["comment"] + data["code"],
            )


class HeaderBar(Static):

    @work(description="Updating header with CLOC version and elapsed time")
    async def update_header(self, header_data: ClocHeader) -> None:
        """Updates the header with CLOC version and elapsed time."""
        self.update(
            f"Running on CLOC v{header_data['cloc_version']}\n"
            f"Elapsed time: {header_data['elapsed_seconds']:.2f} sec | "
            f"Files counted: {header_data['n_files']} | "
            f"Lines counted: {header_data['n_lines']}"
        )


class SummaryBar(Horizontal):
    """A horizontal bar to display summary statistics."""

    def compose(self) -> ComposeResult:
        """Compose the summary bar with static text."""
        yield Static("SUM:  ", id="sum_label")
        yield Static(id="sum_files")
        yield Static(id="sum_blank")
        yield Static(id="sum_comment")
        yield Static(id="sum_code")
        yield Static(id="sum_total")
        yield Static(id="sum_filler")

    def on_mount(self) -> None:
        # The +2s here are all to account for the padding on both sides of each column.
        # I dont set sum_label because it has a width of 1fr in Textual.
        self.query_one("#sum_files").styles.width = CustomDataTable.COL_SIZES["language"] + 2
        self.query_one("#sum_blank").styles.width = CustomDataTable.COL_SIZES["blank"] + 2
        self.query_one("#sum_comment").styles.width = CustomDataTable.COL_SIZES["comment"] + 2
        self.query_one("#sum_code").styles.width = CustomDataTable.COL_SIZES["code"] + 2
        self.query_one("#sum_total").styles.width = CustomDataTable.COL_SIZES["total"] + 2

    @work(description="Updating summary statistics")
    async def update_summary(self, summary_data: ClocSummaryStats) -> None:

        self.query_one("#sum_files", Static).update(
            f"{summary_data['nFiles']} files"
        )
        self.query_one("#sum_blank", Static).update(
            f"{summary_data['blank']}"
        )
        self.query_one("#sum_comment", Static).update(
            f"{summary_data['comment']}"
        )
        self.query_one("#sum_code", Static).update(
            f"{summary_data['code']}"
        )
        self.query_one("#sum_total", Static).update(
            f"{summary_data['blank'] + summary_data['comment'] + summary_data['code']}"
        )


class TableScreen(Screen[None]):

    BINDINGS = [
        Binding("1", "sort_column('path')", "Path"),
        Binding("2", "sort_column('language')", "Language"),
        Binding("3", "sort_column('blank')", "Blank Lines"),
        Binding("4", "sort_column('comment')", "Comment Lines"),
        Binding("5", "sort_column('code')", "Code Lines"),
        Binding("6", "sort_column('total')", "Total"),
    ]

    def __init__(self, worker_result: ClocTUI.WorkerFinished):
        """Initializes the TableScreen with the CLOC JSON result."""
        super().__init__()
        self.header_data = worker_result.header_data
        self.summary_data = worker_result.summary_data
        self.file_data = worker_result.files_data

    def compose(self) -> ComposeResult:

        yield HeaderBar()
        yield CustomDataTable()
        yield SummaryBar()
        yield Static("[dim yellow]1-6[/] to sort columns", id="footer_static")
        yield Static("[italic]Press ctrl+q to exit", id="quit_message")

    async def on_mount(self) -> None:
        
        header = self.query_one(HeaderBar)  #       the first two can be started in parallel
        header.update_header(self.header_data)

        summary = self.query_one(SummaryBar)
        summary.update_summary(self.summary_data)

        table = self.query_one(CustomDataTable)  #          the last one we must wait for
        table_worker = table.update_table(self.file_data)   # in order for sorting to work correctly
        await table_worker.wait()

        await self.run_action("sort_column('total')")

    @on(CustomDataTable.UpdateSummarySize)
    def update_summary_size(self, message: CustomDataTable.UpdateSummarySize) -> None:
        "Adjust first column of summary row when table is resized."
        self.query_one("#sum_label", Static).styles.width = message.size

    def action_sort_column(self, column_key: str) -> None:
        table = self.query_one(CustomDataTable)
        column = table.columns[ColumnKey(column_key)]
        table.sort_column(column, column.key)
        

class ClocTUI(App[None]):

    CSS_PATH = "styles.tcss"

    timeout = 15  # seconds
    working_directory = "./"  #! should this be same as dir_to_scan?

    class WorkerFinished(Message):
        def __init__(
                self,
                header_data: ClocHeader,
                summary_data: ClocSummaryStats,
                files_data: dict[str, ClocFileStats],
        ) -> None:
            super().__init__()
            self.header_data = header_data
            self.summary_data = summary_data
            self.files_data = files_data

    def __init__(self, dir_to_scan: str) -> None:
        """Initializes the ClocTUI application.

        Args:
            dir_to_scan (str): The directory to scan for CLOC stats.
        """
        super().__init__()
        self.dir_to_scan = dir_to_scan

    def compose(self) -> ComposeResult:

        with Horizontal(id="spinner_container"):
            yield SpinnerWidget(text="Counting Lines of Code", spinner_type="line")
            yield SpinnerWidget(spinner_type="simpleDotsScrolling")

    def on_mount(self) -> None:
        if self._driver and self._driver.is_inline:
            self.query_one("#spinner_container").add_class("inline")
        else:
            self.query_one("#spinner_container").add_class("fullscreen")

    def on_ready(self) -> None:

        if not self.check_cloc_installed():
            self.push_screen(CLOCNotInstalledScreen())
            return
        self.run_worker(
            self.execute_cloc,
            description="Executing CLOC process",
            thread=True
        )

    def execute_cloc(self) -> None:
        """Executes the CLOC command and returns the parsed JSON result."""

        cloc = (
            CLOC()
            .add_flag("--by-file")
            .add_flag("--json")
            .add_option("--timeout", self.timeout)
            .set_working_directory(self.working_directory)
            .add_argument(self.dir_to_scan)
        )

        try:
            output = cloc.execute()
        except CLOCException as e:
            raise e
        
        result: ClocJsonResult = json.loads(output)
        header_data: ClocHeader = cast(ClocHeader, result["header"])
        summary_data: ClocSummaryStats = cast(ClocSummaryStats, result["SUM"])
        files_data: dict[str, ClocFileStats] = {}

        for key, value in result.items():
            if key in ["header", "SUM"]:
                continue
            else:
                files_data[key] = cast(ClocFileStats, value)

        self.post_message(
            ClocTUI.WorkerFinished(
                header_data=header_data, summary_data=summary_data, files_data=files_data
            )
        )

    @on(WorkerFinished)
    async def worker_finished(self, message: WorkerFinished) -> None:

        await self.push_screen(TableScreen(message))


    def check_cloc_installed(self) -> bool:
        """Checks if CLOC is installed on the system."""
        try:
            # Use shutil.which to check if cloc is in PATH
            if shutil.which("cloc") is None:
                return False
            # Verify cloc can be executed
            subprocess.run(
                ["cloc", "--version"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
