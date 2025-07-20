# CLOCTUI

<img width="1496" height="838" alt="preview" src="https://github.com/user-attachments/assets/9794bfe9-df5a-479f-8ced-9c316c19dfd9" />

CLOCTUI is a terminal user interface (TUI) for the [CLOC](https://github.com/AlDanial/cloc) code analysis tool, built using the [Textual](https://github.com/Textualize/textual) framework.

CLOCTUI runs CLOC under the hood and then displays the results in an interactive table. It makes the results of CLOC much more pleasant to view, especially for large code bases.

## Features

- Group by language, directory, or show all individual files. This works the same as CLOC's different modes, but interactive.
- Sort any column in the table by clicking the header or using keyboard shortcuts.
- You can run in Inline mode (default), or run in fullscreen mode with the `-f` flag.

## Requirements

CLOCTUI requires Python 3.10 or later and the [CLOC](https://github.com/AlDanial/cloc) command line tool to be installed on your system.

It's also recommended to have a python tool manager such as [UV](https://docs.astral.sh/uv/) or [PipX](https://pipx.pypa.io/stable/) installed to manage the installation of CLOCTUI.

## Test without installing

You can test CLOCTUI without installing it by using [UV](https://docs.astral.sh/uv/) or [PipX](https://pipx.pypa.io/stable/).

Using the `uvx` or `pipx run` commands:  
Enter `uvx cloctui` (or `pipx run`) followed by the path you want to scan as the only argument:

```sh
uvx cloctui src
```

```sh
pipx run cloctui src
```

Both the above commands will run CLOC on the `src` directory and display the results.

A dot would likewise scan the current directory:

```sh
uvx cloctui .
```

## How to Install

The recommended way to use CLOCTUI is as a global tool managed with [UV](https://docs.astral.sh/uv/) or [PipX](https://pipx.pypa.io/stable/).

```sh
uv tool install cloctui
```

```sh
pipx install cloctui
```

Once installed, you can use the `cloctui` command anywhere. To scan the `src` folder in your current directory:

```sh
cloctui src
```

## Fullscreen mode

You can use the `-f` flag to run in Fullscreen mode

```sh
cloctui src -f
```

## Future roadmap

CLOC is an awesome program, and there's numerous features it has which are not integrated into CLOCTUI. In the future if this tool gets any serious usage, I'd be more than happy to consider adding more cool CLOC feature integrations.

## Questions, issues, suggestions?

Feel free to raise issues and bugs in the issues section, and post any ideas / feature requests on the [Ideas discussion board](https://github.com/edward-jazzhands/cloctui/discussions).

## Credits and License

CLOCTUI is developed by Edward Jazzhands

A core class for this project was copied from Stefano Stone:
https://github.com/USIREVEAL/pycloc

It was modified by Edward Jazzhands (added all type hints and improved docstrings).

Both CLOCTUI and pycloc are licensed under the MIT License.
