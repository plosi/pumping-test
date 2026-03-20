import numpy as np
import plotly.graph_objects as go
from models import DrawdownFit

# Consistent colour palette across all plots
COLOURS = {
    "data":     "#1f77b4",   # blue — raw measurements
    "fit":      "#d62728",   # red — fit line
    "linear":   "#ff7f0e",   # orange — BQ (linear losses)
    "total":    "#1f77b4",   # blue — BQ + CQ² (total losses)
    "critical": "#2ca02c",   # green — critical yield marker
}

def generate_fit_line(
    x: np.ndarray,
    fit: DrawdownFit,
    n_points: int = 200,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Generate a smooth fit line from a DrawdownFit over the range of x.
    Returns (x_line, y_line) ready to pass to go.Scatter.

    The fit equation is: s = slope * ln(x) + intercept
    """
    x_range = np.linspace(x.min(), x.max(), n_points)
    y_range = fit.slope * np.log(x_range) + fit.intercept
    return x_range, y_range


def apply_default_layout(fig: go.Figure, title: str, x_label: str, y_label: str) -> None:
    """Apply consistent layout to any figure. Mutates fig in place."""
    fig.update_layout(
        title=title,
        xaxis_title=x_label,
        yaxis_title=y_label,
        template="plotly_white",
        hovermode="x unified",
    )