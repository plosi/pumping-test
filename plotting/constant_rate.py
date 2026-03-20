import plotly.graph_objects as go
import plotly.express as px
from plotting.common import COLOURS, apply_default_layout
from models import PumpingTest, ConstantRateResult
from typing import Optional
import numpy as np


def plot_constant_preview(
    test: PumpingTest,
    title: Optional[str] = None,
) -> go.Figure:
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=test.time_series,
            y=test.level_series,
            mode="markers",
            name="Water Level"
        )
    )
    fig.update_yaxes(range=[None, 0], autorange = "max reversed")
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
            name="Drawdown semi-log"
        )
    )

    # Evaluate fit line over a dense range — skip t=0 since log(0) is undefined
    t_line = np.linspace(test.time_series[1], test.time_series[-1], 200)
    s_line = result.fit.slope * np.log(t_line) + result.fit.intercept

    fig.add_trace(
        go.Scatter(
            x=t_line,
            y=s_line,
            mode="lines",
            name=f"Cooper-Jacob fit (R²={result.fit.r_squared:.3f})"
        )
    )

    # fig.update_yaxes(range=[None, 0], autorange = "max reversed")
    fig.update_xaxes(type="log")
    fig.update_yaxes(autorange="reversed")
    apply_default_layout(
        fig=fig,
        title=title,
        x_label="Elapsed time [min] - log",
        y_label="Drawdown [m]"
    )
    return fig