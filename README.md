# CLOCTUI

![badge](https://img.shields.io/badge/linted-Ruff-blue?&logo=ruff)
![badge](https://img.shields.io/badge/formatted-black-black?)
![badge](https://img.shields.io/badge/type_checked-MyPy-blue?&logo=python)
![badge](https://img.shields.io/badge/license-MIT-blue?)
[![Framework: Textual](https://img.shields.io/badge/framework-Textual-5967FF?logo=python)](https://www.textualize.io/)

CLOCTUI is a terminal user interface (TUI) for the CLOC code analysis tool, built using the Textual framework. It provides an interactive way to analyze code metrics directly from the terminal.

CLOCTUI runs CLOC under the hood and then displays the results in an interactive Textual table. It supports various features such as sorting and filtering the results, making it easier to analyze codebases.

## How To Use

CLOCTUI is designed to be run from the command line using either `pipx` or `uvx`. It requires Python 3.10 or higher.

Enter the path you want to scan as the only argument:

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

Use the `--help` option for an explanation in your terminal.

## Questions, issues, suggestions?

Feel free to post an issue.

## Video

Coming soon!

## Credits and License

CLOCTUI is developed by Edward Jazzhands

A core class for this project was copied from Stefano Stone:
https://github.com/USIREVEAL/pycloc

It was modified by Edward Jazzhands (added all type hints and improved docstrings).

Both CLOCTUI and pycloc are licensed under the MIT License.
