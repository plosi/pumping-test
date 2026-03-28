from models import PumpingTest, ConstantRateResult, DrawdownFit
from typing import Optional
import numpy as np


MACDONALD_YIELD_COEFFICIENT = 4.0
COOPER_JACOB_COEFF = 0.183  # ln(10) / (4π), dimensionless
HOURS_PER_DAY = 24.0

def analyse_constant_rate(
    test: PumpingTest,
    fit_start_idx: int = 1, # Skip t=0 (log(0) is undefined)
    fit_end_idx: Optional[int] = None,  # If None, will use all remaining points
    fit2_start_idx: Optional[int] = None,   # None = no second fit
    fit2_end_idx: Optional[int] = None,
) -> ConstantRateResult:
    """
    Analyse a constant-rate pumping test using the Cooper-Jacob straight-line method.

        T = 0.183 * Q / ds

    where ds is the drawdown per log cycle read from the semi-log plot,
    and Q is the pumping rate in m³/day.

    Args:
        test:          A ConstantRateTest instance with measurements.
        fit_start_idx: Index of the first measurement to include in the fit.
                       Defaults to 1 to skip t=0 where log is undefined.
        fit_end_idx:   Index of the last measurement (exclusive). Defaults to
                       all remaining points.

    Returns:
        ConstantRateResult with transmissivity, estimated yield, and fit details.

    Raises:
        ValueError: If the fit window contains fewer than 2 points,
                    or if any time value in the window is <= 0.

    Note:
        The Cooper-Jacob approximation is only valid when u = r²S/(4Tt) < 0.05.
        Choose fit_start_idx to exclude early-time non-linear data.

    Reference:
        ICRC (2011), Technical Review, Section 4.2
    """
    # Get drawdown series and time series
    drawdown = test.drawdown_series
    time = test.time_series

    def _compute_fit(start: int, end: Optional[int]) -> tuple[DrawdownFit, float, float]:
        """Inner helper — compute fit, T, and yield for one window."""
        fit_time = time[start:end]
        fit_drawdown = drawdown[start:end]

        if len(fit_time) < 2:
            raise ValueError(
                f"Fit window too small: {len(fit_time)} point(s). "
                f"Adjust fit_start_idx ({start}) and fit_end_idx ({end})."
            )
        if np.any(fit_time <= 0):
            raise ValueError("Fit window contains non-positive time values.")

        log_time = np.log(fit_time)
        slope, intercept = np.polyfit(log_time, fit_drawdown, 1)

        y_pred = slope * log_time + intercept
        ss_res = np.sum((fit_drawdown - y_pred) ** 2)
        ss_tot = np.sum((fit_drawdown - np.mean(fit_drawdown)) ** 2)
        r_squared = float(1 - ss_res / ss_tot) if ss_tot > 0 else 0.0

        ds = slope * np.log(10)
        flowrate_m3day = test.flowrate_m3h * HOURS_PER_DAY
        T = COOPER_JACOB_COEFF * flowrate_m3day / ds
        estimated_yield = MACDONALD_YIELD_COEFFICIENT * T

        fit = DrawdownFit(
            slope=slope,
            intercept=intercept,
            drawdown_per_log_cycle=ds,
            n_points_used=len(fit_time),
            r_squared=r_squared,
        )
        return fit, T, estimated_yield

    fit, T, estimated_yield = _compute_fit(fit_start_idx, fit_end_idx)
    flowrate_m3day = test.flowrate_m3h * HOURS_PER_DAY

    # Second fit — only if both start indices are provided
    fit2, T2, yield2 = None, None, None
    if fit2_start_idx is not None:
        fit2, T2, yield2 = _compute_fit(fit2_start_idx, fit2_end_idx)

    return ConstantRateResult(
        fit=fit,
        transmissivity_m2day=T,
        estimated_yield_m3day=estimated_yield,
        flowrate_m3day=flowrate_m3day,
        fit2=fit2,
        transmissivity2_m2day=T2,
        estimated_yield2_m3day=yield2,
    )
