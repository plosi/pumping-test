import plotly.graph_objects as go
import plotly.express as px
from plotting.common import COLOURS, apply_default_layout
from models import PumpingTest, ConstantRateResult
from typing import Optional
import numpy as np


def plot_constant_preview(
    test: PumpingTest,
    title: Optional[str] = None,
    scale_axis: Optional[bool] = False
) -> go.Figure:
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=test.time_series,
            y=test.level_series,
            mode="markers",
            name="Water Level",
            marker=dict(color=COLOURS["data"])
        )
    )
    y_min = test.level_series[0] if scale_axis else 0
    fig.update_yaxes(range=[None, y_min], autorange = "max reversed")
    apply_default_layout(
        fig=fig,
        title=title,
        x_label="Elapsed time [min]",
        y_label="Water level [mbd]"
    )
    return fig

def plot_constant_semilog(
    test: PumpingTest,
    result: ConstantRateResult,
    title: Optional[str] = None
) -> go.Figure:
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=test.time_series,
            y=test.drawdown_series,
            mode="markers",
            name="Drawdown",
            marker=dict(color=COLOURS["data"]),
        )
    )

    t_line = np.linspace(test.time_series[1], test.time_series[-1], 200)

    # First fit
    s_line = result.fit.slope * np.log(t_line) + result.fit.intercept
    fig.add_trace(
        go.Scatter(
            x=t_line,
            y=s_line,
            mode="lines",
            name=f"Fit 1 — T={result.transmissivity_m2day:.1f} m²/day (R²={result.fit.r_squared:.3f})",
            line=dict(color=COLOURS["fit"], width=1.5),
        )
    )

    # Second fit — only if present
    if result.fit2 is not None:
        s_line2 = result.fit2.slope * np.log(t_line) + result.fit2.intercept
        fig.add_trace(
            go.Scatter(
                x=t_line,
                y=s_line2,
                mode="lines",
                name=f"Fit 2 — T={result.transmissivity2_m2day:.1f} m²/day (R²={result.fit2.r_squared:.3f})",
                line=dict(color="#9467bd", width=1.5, dash="dash"),
            )
        )

    fig.update_xaxes(
        type="log",
        minor=dict(showgrid=True, gridcolor="lightgrey", gridwidth=0.5),
        showgrid=True,
    )
    fig.update_yaxes(autorange="reversed")
    apply_default_layout(
        fig=fig,
        title=title,
        x_label="Elapsed time [min] - log scale",
        y_label="Drawdown [m]",
    )
    return fig