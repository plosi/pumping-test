from typing import Annotated, Optional
from pathlib import Path
import typer
import plotly.graph_objects as go


def deliver_plot(fig: go.Figure, output: Optional[Path] = None) -> None:
    if output is not None:
        output = Path(output)
    
    if output is None:
        fig.show()   # opens browser
    elif output.suffix == ".html":
        fig.write_html(str(output))
        typer.echo(f"Plot saved to {output}")
    elif output.suffix in (".png", ".svg", ".pdf"):
        fig.write_image(str(output))  # requires kaleido: pip install kaleido
        typer.echo(f"Plot saved to {output}")
    else:
        typer.echo(f"Unsupported output format '{output.suffix}'. Use .html, .png, or .svg.", err=True)
        raise typer.Exit(code=1)

def deliver_plots(figures: list[go.Figure], outputs: Optional[list[Path]]) -> None:
    """
    Save or display multiple plots.
    If outputs is None, all figures open in the browser.
    If outputs is provided, it must match the number of figures exactly.
    """
    if outputs is None:
        for fig in figures:
            deliver_plot(fig)
        return

    if len(outputs) != len(figures):
        typer.echo(
            f"Error: {len(figures)} plot(s) produced but "
            f"{len(outputs)} --output path(s) given. "
            f"Provide exactly {len(figures)} --output flag(s).",
            err=True,
        )
        raise typer.Exit(code=1)

    for fig, path in zip(figures, outputs):
        deliver_plot(fig, path)
