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
import json
from pathlib import Path
from enum import Enum
from functools import partial

# Textual imports
from textual import on, work, events

# from textual.worker import Worker
from textual.app import App, ComposeResult
from textual.widgets import Static, DataTable, Button  # , Input
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


class SortableText(Text):

    def __lt__(self, other: object) -> bool:
        if isinstance(other, str):
            return self.plain < other
        if isinstance(other, Text):
            return self.plain < other.plain
        return NotImplemented


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


class CustomDataTable(DataTable[Any]):

    class UpdateSummarySize(Message):
        def __init__(self, size: int, update_mode: CustomDataTable.UpdateMode) -> None:
            super().__init__()
            self.size = size
            "The new size for the summary row's first column."
            self.update_mode = update_mode

    class TableInitialized(Message):
        pass

    class SortingStatus(Enum):
        UNSORTED = 0  #     [-] unsorted
        ASCENDING = 1  #    [↑] ascending (reverse = True)
        DESCENDING = 2  #   [↓] descending (reverse = False)

    class UpdateMode(Enum):
        NO_GROUP = 0
        GROUP_BY_LANG = 1
        GROUP_BY_DIR = 2

    # ** Source of Truth ** #
    COL_SIZES = {
        "path": 25,  # dynamic column minimum
        "language": 14,
        "blank": 7,
        "comment": 9,
        "code": 7,
        "total": 9,
    }
    other_cols_total = sum(COL_SIZES.values()) - COL_SIZES["path"]

    def __init__(
        self,
        files_data_grouped: dict[str, dict[str, ClocFileStats]],
        group_mode: CustomDataTable.UpdateMode,
    ) -> None:
        super().__init__(
            zebra_stripes=True,
            show_cursor=False,
            # cursor_type="column",
        )
        # self.files_data_grouped = files_data_grouped
        self.files_data = files_data_grouped["no_group"]
        self.files_by_language = files_data_grouped["files_by_lang"]
        self.files_by_dir = files_data_grouped["files_by_dir"]
        self.initialized = False

        self.group_mode: CustomDataTable.UpdateMode = group_mode

        self.sort_status: dict[str, CustomDataTable.SortingStatus] = {
            "path": CustomDataTable.SortingStatus.UNSORTED,
            "language": CustomDataTable.SortingStatus.UNSORTED,
            "blank": CustomDataTable.SortingStatus.UNSORTED,
            "comment": CustomDataTable.SortingStatus.UNSORTED,
            "code": CustomDataTable.SortingStatus.UNSORTED,
            "total": CustomDataTable.SortingStatus.UNSORTED,
        }
        self.add_column("path [dark_orange]-[/]", key="path")
        self.add_column("language [dark_orange]-[/]", width=self.COL_SIZES["language"], key="language")
        self.add_column("blank [dark_orange]-[/]", width=self.COL_SIZES["blank"], key="blank")
        self.add_column("comment [dark_orange]-[/]", width=self.COL_SIZES["comment"], key="comment")
        self.add_column("code [dark_orange]-[/]", width=self.COL_SIZES["code"], key="code")
        self.add_column("total [dark_orange]-[/]", width=self.COL_SIZES["total"], key="total")

    def on_mount(self) -> None:

        if self.group_mode == CustomDataTable.UpdateMode.NO_GROUP:
            self.update_table(self.files_data, CustomDataTable.UpdateMode.NO_GROUP)
        elif self.group_mode == CustomDataTable.UpdateMode.GROUP_BY_LANG:
            self.update_table(self.files_by_language, CustomDataTable.UpdateMode.GROUP_BY_LANG)
        elif self.group_mode == CustomDataTable.UpdateMode.GROUP_BY_DIR:
            self.update_table(self.files_by_dir, CustomDataTable.UpdateMode.GROUP_BY_DIR)
        else:
            raise RuntimeError(f"Invalid group mode {self.group_mode}")

    def on_resize(self) -> None:
        self.log("on_resize called in table")
        if self.initialized and self.group_mode:
            self.calculate_first_column_size(self.group_mode)

    def update_table(
        self,
        file_data: dict[str, ClocFileStats],
        update_mode: CustomDataTable.UpdateMode,
    ) -> None:

        for key, data in file_data.items():

            path_obj = Path(key)  # path object simplifies the file checking
            rich_textized = SortableText(key, overflow="ellipsis")
            if path_obj.is_file():
                # This will colorize the file extension in orange, if there is one
                ext_index = key.rindex(path_obj.suffix) if path_obj.suffix else None
                if ext_index is not None:
                    rich_textized.stylize(style="dark_orange", start=ext_index)

            self.add_row(
                rich_textized,
                data["language"],
                data["blank"],
                data["comment"],
                data["code"],
                data["blank"] + data["comment"] + data["code"],
            )

        if update_mode == CustomDataTable.UpdateMode.GROUP_BY_LANG:
            self.remove_column(ColumnKey("path"))
            self.sort_status.pop("path", None)
        elif update_mode == CustomDataTable.UpdateMode.GROUP_BY_DIR:
            self.remove_column(ColumnKey("language"))
            self.sort_status.pop("language", None)

        self.call_after_refresh(self.calculate_first_column_size, update_mode=update_mode)

    def calculate_first_column_size(self, update_mode: CustomDataTable.UpdateMode) -> None:

        # Account for padding on both sides of each column:
        total_cell_padding = (self.cell_padding * 2) * len(self.columns)

        # Pretty obvious how this works I think:
        first_col_max_width = self.size.width - self.other_cols_total - total_cell_padding

        if (
            update_mode == CustomDataTable.UpdateMode.NO_GROUP
            or update_mode == CustomDataTable.UpdateMode.GROUP_BY_DIR
        ):
            first_col = self.columns[ColumnKey("path")]
        else:
            assert update_mode == CustomDataTable.UpdateMode.GROUP_BY_LANG
            first_col = self.columns[ColumnKey("language")]

        if first_col.content_width > first_col_max_width:
            first_col.auto_width = False
            first_col.width = first_col_max_width
            self.post_message(
                CustomDataTable.UpdateSummarySize(
                    size=first_col_max_width + 2,
                    update_mode=update_mode,
                )
            )
        elif first_col.content_width < self.COL_SIZES["path"]:
            first_col.auto_width = False
            first_col.width = self.COL_SIZES["path"]
            self.post_message(
                CustomDataTable.UpdateSummarySize(
                    size=self.COL_SIZES["path"] + 2,
                    update_mode=update_mode,
                )
            )
        else:
            first_col.auto_width = True
            self.post_message(
                CustomDataTable.UpdateSummarySize(
                    size=first_col.content_width + 2,
                    update_mode=update_mode,
                )
            )

        self.call_after_refresh(self.custom_refresh)
        self.refresh()

    def custom_refresh(self) -> None:
        self.refresh()
        if not self.initialized:
            self.initialized = True
            self.post_message(CustomDataTable.TableInitialized())

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
        # to sort. Reset all columns to unsorted.
        if self.sort_status[value] == self.SortingStatus.UNSORTED:
            for key in self.sort_status:
                self.sort_status[key] = self.SortingStatus.UNSORTED
                col_index = self.get_column_index(key)
                col = self.ordered_columns[col_index]
                col.label = Text.from_markup(f"{key} [dark_orange]-[/]")

            # Now set chosen column to ascending:
            self.sort_status[value] = self.SortingStatus.ASCENDING
            self.sort(column_key, reverse=True)
            column.label = Text.from_markup(f"{value} [dark_orange]↑[/]")

        # For the other two conditions, we just toggle ascending/descending
        elif self.sort_status[value] == self.SortingStatus.ASCENDING:
            self.sort_status[value] = self.SortingStatus.DESCENDING
            self.sort(value, reverse=False)
            column.label = Text.from_markup(f"{value} [dark_orange]↓[/]")
        elif self.sort_status[value] == self.SortingStatus.DESCENDING:
            self.sort_status[value] = self.SortingStatus.ASCENDING
            self.sort(column_key, reverse=True)
            column.label = Text.from_markup(f"{value} [dark_orange]↑[/]")
        else:
            raise ValueError(
                f"Sort status for {value} is '{self.sort_status[value]}', did not meet any expected values."
            )


class HeaderBar(Static):

    def __init__(self, header_data: ClocHeader) -> None:
        """Initializes the HeaderBar with CLOC version and elapsed time."""
        super().__init__()
        self.header_data = header_data

    def on_mount(self) -> None:
        self.update_header(self.header_data)

    @work(description="Updating header with CLOC version and elapsed time")
    async def update_header(self, header_data: ClocHeader) -> None:
        """Updates the header with CLOC version and elapsed time."""
        inline_msg = ""
        if self.app.is_inline:
            inline_msg = " | Resizing in this mode may cause display issues."
        self.update(
            f"Running on CLOC v{header_data['cloc_version']}\n"
            f"Elapsed time: {header_data['elapsed_seconds']:.2f} sec │ "
            f"Files counted: {header_data['n_files']} │ "
            f"Lines counted: {header_data['n_lines']}\n"
            f"App mode: {'Inline' if self.app.is_inline else 'Fullscreen'}"
            f"{inline_msg}"
        )


class SummaryBar(Horizontal):
    """A horizontal bar to display summary statistics."""

    def __init__(self, summary_data: ClocSummaryStats) -> None:
        """Initializes the SummaryBar with CLOC summary statistics."""
        super().__init__()
        self.summary_data = summary_data

    def compose(self) -> ComposeResult:
        """Compose the summary bar with static text."""
        yield Static("SUM:  ", id="sum_label", classes="sum_cell")
        yield Static(id="sum_files", classes="sum_cell")
        yield Static(id="sum_blank", classes="sum_cell")
        yield Static(id="sum_comment", classes="sum_cell")
        yield Static(id="sum_code", classes="sum_cell")
        yield Static(id="sum_total", classes="sum_cell")
        yield Static(id="sum_filler", classes="sum_cell")

    def on_mount(self) -> None:
        # The +2s here are all to account for the padding on both sides of each column.
        # I dont set sum_label because it has a width of 1fr in Textual.

        # I didn't use CSS for this because I want the COL_SIZES dictionary to be
        # the one source of truth for the column widths.
        self.query_one("#sum_files").styles.width = CustomDataTable.COL_SIZES["language"] + 2
        self.query_one("#sum_blank").styles.width = CustomDataTable.COL_SIZES["blank"] + 2
        self.query_one("#sum_comment").styles.width = CustomDataTable.COL_SIZES["comment"] + 2
        self.query_one("#sum_code").styles.width = CustomDataTable.COL_SIZES["code"] + 2
        self.query_one("#sum_total").styles.width = CustomDataTable.COL_SIZES["total"] + 2

        self.update_summary(self.summary_data)

    @work(description="Updating summary statistics")
    async def update_summary(self, summary_data: ClocSummaryStats) -> None:

        self.query_one("#sum_files", Static).update(f"{summary_data['nFiles']} files")
        self.query_one("#sum_blank", Static).update(f"{summary_data['blank']}")
        self.query_one("#sum_comment", Static).update(f"{summary_data['comment']}")
        self.query_one("#sum_code", Static).update(f"{summary_data['code']}")
        self.query_one("#sum_total", Static).update(
            f"{summary_data['blank'] + summary_data['comment'] + summary_data['code']}"
        )

    def update_size(self, message: CustomDataTable.UpdateSummarySize) -> None:
        mode = message.update_mode
        first_col_size = message.size
        sum_label = self.query_one("#sum_label", Static)
        files_label = self.query_one("#sum_files", Static)
        if mode == CustomDataTable.UpdateMode.NO_GROUP:
            sum_label.display = True
            sum_label.styles.width = first_col_size
            files_label.styles.width = CustomDataTable.COL_SIZES["language"] + 2
        elif (
            mode == CustomDataTable.UpdateMode.GROUP_BY_LANG
            or mode == CustomDataTable.UpdateMode.GROUP_BY_DIR
        ):
            sum_label.display = False
            files_label.styles.width = first_col_size


class OptionsBar(Horizontal):
    """A horizontal bar to display options or instructions."""

    class GroupByLang(Message):
        pass

    class GroupByDir(Message):
        pass

    class NoGroup(Message):
        pass

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        with Horizontal(id="options_buttons_container", classes="button_container"):
            yield Button("Show files", id="button_no_group", compact=True)
            yield Button("Group by language", id="button_lang", compact=True)
            yield Button("Group by dir", id="button_dir", compact=True)

        # ~ FUTURE VERSION PLAN:
        # yield Input(placeholder="Filter by path", id="options_input")

    def on_button_pressed(self, event: Button.Pressed) -> None:

        if event.button.id == "button_lang":
            self.post_message(OptionsBar.GroupByLang())
        elif event.button.id == "button_dir":
            self.post_message(OptionsBar.GroupByDir())
        elif event.button.id == "button_no_group":
            self.post_message(OptionsBar.NoGroup())


class TableScreen(Screen[None]):

    BINDINGS = [
        Binding("1", "sort_column(0)", "Sort Column 1"),
        Binding("2", "sort_column(1)", "Sort Column 2"),
        Binding("3", "sort_column(2)", "Sort Column 3"),
        Binding("4", "sort_column(3)", "Sort Column 4"),
        Binding("5", "sort_column(4)", "Sort Column 5"),
        Binding("6", "sort_column(5)", "Sort Column 6"),
    ]

    def __init__(self, worker_result: ClocTUI.WorkerFinished, group_mode: CustomDataTable.UpdateMode):
        """Initializes the TableScreen with the CLOC JSON result."""
        super().__init__()
        self.header_data = worker_result.header_data
        self.summary_data = worker_result.summary_data
        self.files_data_grouped = worker_result.files_data_grouped
        self.group_mode = group_mode
        self.ctrl_nums = "1-6" if group_mode == CustomDataTable.UpdateMode.NO_GROUP else "1-5"

    def compose(self) -> ComposeResult:

        with Vertical(id="header_container"):
            yield HeaderBar(self.header_data)
            yield OptionsBar()
        with Vertical(id="table_container"):
            self.table = CustomDataTable(self.files_data_grouped, self.group_mode)
            yield self.table
        with Vertical(id="bottom_container"):
            self.summary_bar = SummaryBar(self.summary_data)
            yield self.summary_bar
            yield Static(
                "[orange]Tab[/] Cycle focus │ "
                f"[orange]{self.ctrl_nums}[/] Sort columns │ "
                "[orange]Click[/] Headers to sort │ "
                "[orange]Ctrl+q[/] Quit",
                id="controls_bar",
            )
            with Horizontal(id="quit_buttons_container", classes="button_container"):
                yield Button("Quit", id="quit_button", compact=True)
                if self.app.is_inline:
                    yield Button("Quit without clearing screen", id="quit_no_clear", compact=True)

    @on(CustomDataTable.TableInitialized)
    async def table_initialized(self) -> None:

        if self.group_mode == CustomDataTable.UpdateMode.NO_GROUP:
            await self.run_action("sort_column(5)")
        else:
            await self.run_action("sort_column(4)")

        # self.app.set_focus(self.query_one(OptionsBar).query_one("#button_no_group"))

    def on_resize(self, event: events.Resize) -> None:
        self.log(f"on_resize called in Screen with height: {event.size.height}")

        table_container = self.query_one("#table_container", Vertical)
        height = event.size.height

        before_max_height_scalar = table_container.styles.max_height
        if before_max_height_scalar is not None:
            self.log(f"{before_max_height_scalar.is_cells = }" f" | {before_max_height_scalar.cells = }")
        else:
            self.log("before_max_height_scalar is not set yet.")

        # the header and bottom containers are 5 and 6 lines tall
        # plus 2 for the top/bottom screen borders that for some reason I cannot
        # get rid of without messing up the layout. So subtract 13 in total.

        table_container.styles.max_height = height - 13
        after_max_height_scalar = table_container.styles.max_height
        if after_max_height_scalar is not None:
            self.log(f"{after_max_height_scalar.is_cells = }" f" | {after_max_height_scalar.cells = }")
        else:
            self.log.error("after_max_height_scalar is not set.")

    @on(CustomDataTable.UpdateSummarySize)
    def update_summary_size(self, message: CustomDataTable.UpdateSummarySize) -> None:
        "Adjust first column of summary row when table is resized."
        self.summary_bar.update_size(message)

    def action_sort_column(self, column_index: int) -> None:

        try:
            column = self.table.ordered_columns[column_index]
        except IndexError:
            return
        else:
            self.table.sort_column(column, column.key)

    @on(Button.Pressed, "#quit_button")
    def quit_button_pressed(self) -> None:
        self.set_timer(0.3, partial(self.exit_app, clear_screen=True))

    @on(Button.Pressed, "#quit_no_clear")
    def quit_button_no_clear_pressed(self) -> None:
        self.set_timer(0.3, partial(self.exit_app, clear_screen=False))

    def exit_app(self, clear_screen: bool = True) -> None:
        if clear_screen:
            self.app._exit_renderables.append("")  # type: ignore[unused-ignore]
        self.app.exit()


class ClocTUI(App[None]):

    class AppMode(Enum):
        INLINE = 0
        FULLSCREEN = 1

    CSS_PATH = "styles.tcss"

    timeout = 15  # seconds
    working_directory = "./"  #! should this be same as dir_to_scan?

    class WorkerFinished(Message):
        def __init__(
            self,
            header_data: ClocHeader,
            summary_data: ClocSummaryStats,
            files_data_grouped: dict[str, dict[str, ClocFileStats]],
        ) -> None:
            super().__init__()
            self.header_data = header_data
            self.summary_data = summary_data
            self.files_data_grouped = files_data_grouped

    def __init__(self, dir_to_scan: str, mode: ClocTUI.AppMode) -> None:
        """
        Args:
            dir_to_scan (str): The directory to scan for CLOC stats.
        """
        self.dir_to_scan = dir_to_scan
        self.mode = mode

        if self.mode == ClocTUI.AppMode.INLINE:
            ansi_color = True
        else:
            ansi_color = False
        super().__init__(ansi_color=ansi_color)

    def compose(self) -> ComposeResult:

        with Horizontal(id="spinner_container"):
            yield SpinnerWidget(text="Counting Lines of Code", spinner_type="line")
            yield SpinnerWidget(spinner_type="simpleDotsScrolling")

    def on_mount(self) -> None:
        if self.is_inline:
            self.query_one("#spinner_container").add_class("inline")
        else:
            self.query_one("#spinner_container").add_class("fullscreen")

    def on_ready(self) -> None:
        self.execute_cloc()

    async def action_quit(self) -> None:
        # this forces it to clear when exiting:
        self._exit_renderables.append("")
        self.exit()

    @work(description="Executing CLOC command", thread=True)
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

        # The header and summary data will come out ready to use and don't
        # require further processing.
        header_data: ClocHeader = cast(ClocHeader, result["header"])
        summary_data: ClocSummaryStats = cast(ClocSummaryStats, result["SUM"])

        # The files data needs to be processed to group by language and directory.
        files_data: dict[str, ClocFileStats] = {}
        files_by_language: dict[str, ClocFileStats] = {}
        files_by_dir: dict[str, ClocFileStats] = {}

        # First separate out the files data from the result.
        for key, value in result.items():
            if key in ["header", "SUM"]:
                continue
            else:
                files_data[key] = cast(ClocFileStats, value)

        for key, data in files_data.items():
            # Group by language
            if data["language"] not in files_by_language:
                files_by_language[data["language"]] = {
                    "blank": 0,
                    "comment": 0,
                    "code": 0,
                    "language": data["language"],
                }
            files_by_language[data["language"]]["blank"] += data["blank"]
            files_by_language[data["language"]]["comment"] += data["comment"]
            files_by_language[data["language"]]["code"] += data["code"]

            # Group by directory
            dir_name = os.path.dirname(key)
            if dir_name not in files_by_dir:
                files_by_dir[dir_name] = {
                    "blank": 0,
                    "comment": 0,
                    "code": 0,
                    "language": dir_name,
                }
            files_by_dir[dir_name]["blank"] += data["blank"]
            files_by_dir[dir_name]["comment"] += data["comment"]
            files_by_dir[dir_name]["code"] += data["code"]

        files_by_language = files_by_language
        files_by_dir = files_by_dir

        files_data_grouped = {
            "no_group": files_data,
            "files_by_lang": files_by_language,
            "files_by_dir": files_by_dir,
        }

        self.worker_finished_msg = ClocTUI.WorkerFinished(
            header_data=header_data,
            summary_data=summary_data,
            files_data_grouped=files_data_grouped,
        )

        self.post_message(self.worker_finished_msg)

    @on(WorkerFinished)
    async def worker_finished(self, message: WorkerFinished) -> None:

        spinner_container = self.query_one("#spinner_container", Horizontal)
        spinner_container.remove()
        await self.push_screen(
            TableScreen(message, group_mode=CustomDataTable.UpdateMode.NO_GROUP),
        )

    @on(OptionsBar.GroupByLang)
    async def group_by_lang(self) -> None:

        table_screen = self.screen
        assert isinstance(table_screen, TableScreen), "Expected TableScreen instance."
        table_screen.dismiss()
        await self.push_screen(
            TableScreen(self.worker_finished_msg, group_mode=CustomDataTable.UpdateMode.GROUP_BY_LANG),
        )

    @on(OptionsBar.GroupByDir)
    async def group_by_dir(self) -> None:

        table_screen = self.screen
        assert isinstance(table_screen, TableScreen), "Expected TableScreen instance."
        table_screen.dismiss()
        await self.push_screen(
            TableScreen(self.worker_finished_msg, group_mode=CustomDataTable.UpdateMode.GROUP_BY_DIR),
        )

    @on(OptionsBar.NoGroup)
    async def no_group(self) -> None:

        table_screen = self.screen
        assert isinstance(table_screen, TableScreen), "Expected TableScreen instance."
        table_screen.dismiss()
        await self.push_screen(
            TableScreen(self.worker_finished_msg, group_mode=CustomDataTable.UpdateMode.NO_GROUP),
        )
