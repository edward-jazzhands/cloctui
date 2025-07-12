from __future__ import annotations

# from typing import get_args, cast
import click


@click.command(context_settings={"ignore_unknown_options": False})
@click.argument("path", type=str, default=None, required=False)
def cli(
    path: str | None,
) -> None:
    """CLI for CLOCTUI"""

    # If no main argument is provided, scan current directory.
    if path is None:
        click.echo("No path provided")

    else:
        from cloctui.main import ClocTUI

        ClocTUI(path).run(inline=True, inline_no_clear=True)


def run() -> None:
    """Entry point for the application."""
    cli()


if __name__ == "__main__":
    cli()
