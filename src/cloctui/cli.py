# stndlib
from __future__ import annotations
import shutil
import subprocess

# libraries
import click

error_message = """\

CLOC is not installed on your system.
Please install CLOC to use this application.
Visit https://github.com/AlDanial/cloc for more information.

Depending your operating system, one of these installation methods may work for you
(all but the last two entries for Windows require a Perl interpreter):

npm install -g cloc              # https://www.npmjs.com/package/cloc
sudo apt install cloc            # Debian, Ubuntu
sudo yum install cloc            # Red Hat, Fedora
sudo dnf install cloc            # Fedora 22 or later
sudo pacman -S cloc              # Arch
yay -S cloc-git                  # Arch AUR (latest git version)
sudo emerge -av dev-util/cloc    # Gentoo https://packages.gentoo.org/packages/dev-util/cloc
sudo apk add cloc                # Alpine Linux
doas pkg_add cloc                # OpenBSD
sudo pkg install cloc            # FreeBSD
sudo port install cloc           # macOS with MacPorts
brew install cloc                # macOS with Homebrew
winget install AlDanial.Cloc     # Windows with winget (might not work, ref https://github.com/AlDanial/cloc/issues/849)
choco install cloc               # Windows with Chocolatey
scoop install cloc               # Windows with Scoop
"""


@click.command(context_settings={"ignore_unknown_options": False})
@click.argument("path", type=str, default=None, required=False)
@click.option(
    "--fullscreen", "-f", is_flag=True, default=False, help="Run in fullscreen / full terminal mode"
)
def cli(path: str | None, fullscreen: bool = False) -> None:
    """
    CLOCTUI - a terminal frontend for CLOC (Count Lines of Code).

    Path must be provided. Use '.' for the current directory or specify a path to a directory.
    """

    # Use shutil.which to check if cloc is in PATH
    if shutil.which("cloc") is None:
        click.echo(error_message)
        return

    # Check if cloc command is available by running it
    try:
        subprocess.run(
            ["cloc", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        click.echo(error_message)
        return

    # After confirming the user has CLOC installed, proceed with checking the path
    # If no main argument is provided, do nothing
    if path is None:
        click.echo(
            "CLOCTUI - a terminal frontend for CLOC (Count Lines of Code).\n\n"
            "Path must be provided. Use '.' for the current directory or specify a path to a directory."
        )
        return

    else:
        from pathlib import Path
        from cloctui.main import ClocTUI

        path_obj = Path(path).expanduser().resolve()
        if not path_obj.exists():
            click.echo(f"Path '{path}' does not exist.")
            return
        
        if not path_obj.is_dir():
            click.echo(f"Path '{path}' is not a directory.")
            return

        inline = not fullscreen

        if fullscreen:
            mode = ClocTUI.AppMode.FULLSCREEN
        else:
            mode = ClocTUI.AppMode.INLINE

        ClocTUI(path, mode=mode).run(inline=inline, inline_no_clear=True)


def run() -> None:
    """Entry point for the application."""
    cli()


if __name__ == "__main__":
    cli()
