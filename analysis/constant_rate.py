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

    if fit_end_idx is None:
        fit_end_idx = len(drawdown)
    
    fit_drawdown = drawdown[fit_start_idx:fit_end_idx]
    fit_time = time[fit_start_idx:fit_end_idx]

    if len(fit_time) < 2:
        raise ValueError(
            f"Fit window too small: {len(fit_time)} point(s). "
            f"Adjust fit_start_idx ({fit_start_idx}) and fit_end_idx ({fit_end_idx})."
        )

    if np.any(fit_time <= 0):
        raise ValueError("Cannot compute log of non-positive time values. Ensure t=0 is excluded from the fit range.")

    # Fit a line to the semi-log plot of drawdown vs. time
    log_time = np.log(fit_time)
    slope, intercept = np.polyfit(log_time, fit_drawdown, 1)

    # Calculate R² for the fit
    y_pred = slope * log_time + intercept
    ss_res = np.sum((fit_drawdown - y_pred) ** 2)
    ss_tot = np.sum((fit_drawdown - np.mean(fit_drawdown)) ** 2)
    r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

    # Calculate drawdown per log cycle (ds)
    ds = slope * np.log(10)  # Convert slope to drawdown per log cycle

    # Calculate transmissivity using Cooper-Jacob formula
    flowrate_m3day = test.flowrate_m3h * HOURS_PER_DAY  # Convert from m³/h to m³/day
    T = COOPER_JACOB_COEFF * flowrate_m3day / ds

    # Estimate yield as per McDonald et al. (2005) - this is a very rough estimate and should be used with caution
    estimated_yield_m3day = MACDONALD_YIELD_COEFFICIENT * T

    return ConstantRateResult(
        fit = DrawdownFit(
            slope = slope,
            intercept = intercept,
            drawdown_per_log_cycle = ds,
            n_points_used = len(fit_time),
            r_squared = r_squared
        ),
        transmissivity_m2day = T,
        estimated_yield_m3day = estimated_yield_m3day,
        flowrate_m3day = flowrate_m3day
    )
