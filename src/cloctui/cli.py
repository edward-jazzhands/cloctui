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
    """CLI for CLOCTUI"""

    # If no main argument is provided, scan current directory.
    if path is None:
        click.echo("No path provided")

    else:

        # Use shutil.which to check if cloc is in PATH
        if shutil.which("cloc") is None:
            click.echo(error_message)
            return

        try:
            subprocess.run(
                ["cloc", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            click.echo(error_message)
            return
        else:
            from cloctui.main import ClocTUI

            inline = not fullscreen
            ClocTUI(path).run(inline=inline)


def run() -> None:
    """Entry point for the application."""
    cli()


if __name__ == "__main__":
    cli()
