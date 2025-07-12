"""main.py - CLOCTUI - A TUI interface for CLOC
========================================================

# ~ Type Checking (Pyright and MyPy) - Strict Mode
# ~ Linting - Ruff
# ~ Formatting - Black - max 110 characters / line
"""

# python standard lib
from __future__ import annotations
from typing import TypedDict, Union, cast
import subprocess
import os
import json

# Textual imports
# from textual import getters
from textual import on
from textual.app import App, ComposeResult
from textual.widgets import Static, DataTable

# from textual.widgets.data_table import ColumnKey
from textual.widgets.data_table import CellType
from textual.screen import Screen
from textual.message import Message
from textual.containers import Horizontal, Vertical
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


class TableScreen(Screen[None]):

    sort_dict_status: dict[str, int] = {
        "path": 0,  # 0 = unsorted
        "language": 0,  # 1 = ascending (reverse = True)
        "blank": 0,  # 2 = descending (reverse = False)
        "comment": 0,
        "code": 0,
        "total": 0,
    }

    def __init__(self, result: ClocJsonResult):
        """Initializes the TableScreen with the CLOC JSON result."""
        super().__init__()
        self.result = result
        self.datatable = DataTable[CellType](id="main_table")  #  type: ignore
        self.sum_datatable = DataTable[CellType](show_header=False, id="summary")  # type: ignore

    def compose(self) -> ComposeResult:

        yield Static(id="header_static")
        yield self.datatable
        with Vertical(id="footer"):
            yield self.sum_datatable
            yield Static("[italic]Press ctrl+q to exit", id="footer_static")

    def on_mount(self) -> None:

        self.call_after_refresh(self.finish_loading)

    def finish_loading(self) -> None:

        if self.size.width == 0:
            raise RuntimeError("Screen size is zero, cannot determine column widths.")

        first_col = self.size.width - 58
        if first_col < 10:
            first_col = 10

        self.datatable.add_column("path [yellow]-[/]", width=first_col, key="path")
        self.datatable.add_column("language [yellow]-[/]", width=14, key="language")
        self.datatable.add_column("blank [yellow]-[/]", width=7, key="blank")
        self.datatable.add_column("comment [yellow]-[/]", width=9, key="comment")
        self.datatable.add_column("code [yellow]-[/]", width=7, key="code")
        self.datatable.add_column("total [yellow]-[/]", width=7, key="total")
        self.sum_datatable.add_column("path", width=first_col)
        self.sum_datatable.add_column("files", width=14)
        self.sum_datatable.add_column("blank", width=7)
        self.sum_datatable.add_column("comment", width=9)
        self.sum_datatable.add_column("code", width=7)
        self.sum_datatable.add_column("total", width=7)

        for key, value in self.result.items():
            if key == "header":
                header: ClocHeader = cast(ClocHeader, value)
                header_static = self.query_one("#header_static", Static)
                header_static.update(
                    f"Running on CLOC v{header['cloc_version']}\n"
                    f"Elapsed time: {header['elapsed_seconds']:.2f} sec | "
                    f"Files counted: {header['n_files']} | Lines counted: {header['n_lines']}"
                )
            elif key == "SUM":
                summary: ClocSummaryStats = cast(ClocSummaryStats, value)

                self.sum_datatable.add_row(
                    "SUM:",
                    f"{summary['nFiles']} files",
                    summary["blank"],
                    summary["comment"],
                    summary["code"],
                    summary["blank"] + summary["comment"] + summary["code"],
                )
            else:
                file_stats: ClocFileStats = cast(ClocFileStats, value)
                self.datatable.add_row(
                    key,  # This is the file path
                    file_stats["language"],
                    file_stats["blank"],
                    file_stats["comment"],
                    file_stats["code"],
                    file_stats["blank"] + file_stats["comment"] + file_stats["code"],
                )

        col_index = self.datatable.get_column_index("total")
        total_col = self.datatable.ordered_columns[col_index]

        message = DataTable.HeaderSelected(self.datatable, total_col.key, col_index, label=total_col.label)
        self.datatable.post_message(message)

    @on(DataTable.HeaderSelected)
    def header_selected(self, event: DataTable.HeaderSelected) -> None:
        """Handles header selection for sorting."""

        if event.column_key.value is None:
            raise ValueError("Tried to sort a column with no key.")
        if event.column_key.value not in self.sort_dict_status:
            raise ValueError(
                f"Unknown column key: {event.column_key.value}. "
                "This should never happen, please report this issue."
            )

        column = self.datatable.ordered_columns[event.column_index]
        value = event.column_key.value

        # if its currently unsorted, that means the user is switching columns
        # to sort. Reset all other columns to unsorted.
        if self.sort_dict_status[value] == 0:
            for key in self.sort_dict_status:
                self.sort_dict_status[key] = 0
                col_index = self.datatable.get_column_index(key)
                col = self.datatable.ordered_columns[col_index]
                col.label = Text.from_markup(f"{key} [yellow]-[/]")
            self.sort_dict_status[value] = 1
            self.datatable.sort(event.column_key, reverse=True)
            column.label = Text.from_markup(f"{value} [yellow]↑[/]")

        # For the other two conditions, we just toggle the sort order
        elif self.sort_dict_status[value] == 1:
            self.sort_dict_status[value] = 2
            self.datatable.sort(value, reverse=False)
            column.label = Text.from_markup(f"{value} [yellow]↓[/]")
        elif self.sort_dict_status[value] == 2:
            self.sort_dict_status[value] = 1
            self.datatable.sort(event.column_key, reverse=True)
            column.label = Text.from_markup(f"{value} [yellow]↑[/]")
        else:
            raise ValueError(
                f"Sort status for {value} is '{self.sort_dict_status[value]}' "
                "did not meet any expected values."
            )

        # self.datatable.update_cell
        # self.datatable.refresh_column(event.column_index)


class ClocTUI(App[None]):

    CSS_PATH = "styles.tcss"

    timeout = 15  # seconds
    working_directory = "./"  #! should this be same as dir_to_scan?

    class WorkerFinished(Message):
        def __init__(self, result: ClocJsonResult):
            super().__init__()
            self.result = result

    def __init__(self, dir_to_scan: str) -> None:
        """Initializes the ClocTUI application.

        Args:
            dir_to_scan (str): The directory to scan for CLOC stats.
        """
        super().__init__()
        self.dir_to_scan = dir_to_scan

    def compose(self) -> ComposeResult:

        with Horizontal():
            yield SpinnerWidget(text="Counting Lines of Code", spinner_type="line")
            yield SpinnerWidget(spinner_type="simpleDotsScrolling")

    def execute_cloc(self) -> None:
        """Executes the CLOC command and returns the parsed JSON result."""

        result: ClocJsonResult = json.loads(
            CLOC()
            .add_flag("--by-file")
            .add_flag("--json")
            .add_option("--timeout", self.timeout)
            .set_working_directory(self.working_directory)
            .add_argument(self.dir_to_scan)
            .execute()
        )
        self.post_message(ClocTUI.WorkerFinished(result=result))

    def on_ready(self) -> None:
        self.run_worker(self.execute_cloc, thread=True)

    @on(WorkerFinished)
    async def worker_finished(self, message: WorkerFinished) -> None:
        self.log.info("CLOC command finished successfully.")
        await self.push_screen(TableScreen(message.result))


# This is for seeing the raw JSON output in the console
# Useful for debugging or testing the CLOC command
if __name__ == "__main__":

    timeout = 15
    working_directory = "./"
    dir_to_scan = "src"

    result: ClocJsonResult = json.loads(
        CLOC()
        .add_flag("--by-file")
        .add_flag("--json")
        .add_option("--timeout", timeout)
        .set_working_directory(working_directory)
        .add_argument(dir_to_scan)
        .execute()
    )
    print(json.dumps(result, indent=4))
