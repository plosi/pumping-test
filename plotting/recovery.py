import plotly.graph_objects as go
from plotting.common import COLOURS, apply_default_layout
from models import PumpingTest, RecoveryResult
from typing import Optional
import numpy as np


def plot_recovery_preview(
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
    y_min = test.level_series[-1] if scale_axis else 0
    fig.update_yaxes(range=[None, y_min], autorange = "max reversed")
    apply_default_layout(
        fig=fig,
        title=title,
        x_label="Elapsed time [min]",
        y_label="Water level [mbd]"
    )
    return fig

def plot_recovery_semilog(
    test: PumpingTest,
    result: RecoveryResult,
    title: Optional[str] = None
) -> go.Figure:
    fig = go.Figure()

    # Compute t/t' ratio — same as in analyse_recovery
    t_prime = test.time_series
    t = test.end_of_pumping_min + t_prime
    time_ratio = t / t_prime

    fig.add_trace(
        go.Scatter(
            x=time_ratio,
            y=test.drawdown_series,
            mode="markers",
            name="Drawdown semi-log",
            marker=dict(color=COLOURS["data"])
        )
    )

    # Fit line over the t/t' range — skip index 0 where t'=0
    ratio_line = np.linspace(time_ratio[1], time_ratio[-1], 200)
    s_line = result.fit.slope * np.log(ratio_line) + result.fit.intercept

    fig.add_trace(
        go.Scatter(
            x=ratio_line,
            y=s_line,
            mode="lines",
            name=f"Cooper-Jacob fit (R²={result.fit.r_squared:.3f})",
            marker=dict(color=COLOURS["fit"])
        )
    )

    fig.update_yaxes(range=[None, 0], autorange = "max reversed")
    fig.update_xaxes(
        type="log",
        minor=dict(
            ticklen=4,
            tickcolor="lightgrey",
            showgrid=True,
            gridcolor="lightgrey",
            gridwidth=0.5,
        ),
        showgrid=True,
        gridcolor="lightgrey",
    )
    # fig.update_yaxes(autorange="reversed")
    apply_default_layout(
        fig=fig,
        title=title,
        x_label="t/t' [-] (log scale)",
        y_label="Drawdown [m]"
    )
    return fig