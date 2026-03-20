from models import PumpingTest, RecoveryResult, DrawdownFit
from typing import Optional
import numpy as np
# import warnings
# warnings.filterwarnings("error", category=RuntimeWarning)

MACDONALD_YIELD_COEFFICIENT = 4.0
COOPER_JACOB_COEFF = 0.183  # ln(10) / (4π), dimensionless
HOURS_PER_DAY = 24.0

def analyse_recovery(
    test: PumpingTest,
    fit_start_idx: int = 1, # Skip t=0 (log(0) is undefined)
    fit_end_idx: Optional[int] = None,  # If None, will use all remaining points
) -> RecoveryResult:
    """
    Analyse a recovery test using the Cooper-Jacob straight-line method on the recovery data.

    Args:
        test:          A RecoveryTest instance with measurements.
        fit_start_idx: Index of the first measurement to include in the fit.
                       Defaults to 1 to skip t=0 where log is undefined.
        fit_end_idx:   Index of the last measurement (exclusive). Defaults to
                       all remaining points.
    
    Returns:
        RecoveryResult with transmissivity, estimated yield, and fit details.
    
    Raises:
        ValueError: If the fit window contains fewer than 2 points,
                    or if any time value in the window is <= 0.
    
    Note:
        The Cooper-Jacob approximation is only valid when u = r²S/(4Tt) < 0.05.
        Choose fit_start_idx to exclude early-time non-linear data.
    """
    # Get drawdown and time series
    drawdown = test.drawdown_series
    t_prime = test.time_series # time since revovery started in minutes
    time = test.end_of_pumping_min + t_prime    # time since pumping started in minutes
    # t/t' ratio for Cooper-Jacob analysis
    time_ratio = np.divide(
        time,
        t_prime,
        out=np.full_like(t_prime, np.nan),  # output array pre-filled with nan
        where=t_prime > 0                    # only divide where this is True
    )

    if fit_end_idx is None:
        fit_end_idx = len(drawdown)
    
    fit_drawdown = drawdown[fit_start_idx:fit_end_idx]
    fit_time = time_ratio[fit_start_idx:fit_end_idx]

    if len(fit_time) < 2:
        raise ValueError(
            f"Fit window too small: {len(fit_time)} point(s). "
            f"Adjust fit_start_idx ({fit_start_idx}) and fit_end_idx ({fit_end_idx})."
        )

    if np.any(fit_time <= 0) or np.any(np.isnan(fit_time)):
        raise ValueError(
            "Fit window contains non-positive or undefined time ratio values. "
            "Ensure fit_start_idx >= 1 to exclude t'=0."
        )

    # Fit a line to the semi-log plot of drawdown vs. time
    log_time = np.log(fit_time)
    slope, intercept = np.polyfit(log_time, fit_drawdown, 1)

    # Calculate R² for the fit
    y_pred = slope * log_time + intercept
    ss_res = np.sum((fit_drawdown - y_pred) ** 2)
    ss_tot = np.sum((fit_drawdown - np.mean(fit_drawdown)) ** 2)
    r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

    # On the t/t' semi-log plot, drawdown decreases as t/t' decreases toward 1,
    # so the slope is expected to be positive (drawdown increases with log(t/t')).
    # If slope is negative, the fit window may be poorly chosen.
    if slope < 0:
        raise ValueError(
            f"Negative slope ({slope:.4f}) suggests a poor fit window. "
            "Check that fit_start_idx excludes early-time data."
        )

    # Calculate drawdown per log cycle (ds)
    ds = slope * np.log(10)  # Convert slope to drawdown per log cycle

    # Calculate the recovery
    if drawdown[0] == 0:
        raise ValueError(
            "Drawdown at the start of recovery is zero — cannot compute recovery percentage. "
            "Check that the static level is set correctly."
        )

    recovery_pct = (1 - drawdown[-1] / drawdown[0]) * 100

    # Calculate transmissivity using Cooper-Jacob formula
    flowrate_m3day = test.flowrate_m3h * HOURS_PER_DAY  # Convert from m³/h to m³/day
    T = COOPER_JACOB_COEFF * flowrate_m3day / ds

    # Estimate yield as per McDonald et al. (2005) - this is a very rough estimate and should be used with caution
    estimated_yield_m3day = MACDONALD_YIELD_COEFFICIENT * T

    return RecoveryResult(
        fit = DrawdownFit(
            slope=slope,
            intercept=intercept,
            drawdown_per_log_cycle=ds,
            n_points_used=len(fit_time),
            r_squared=r_squared
        ),
        recovery_pcg=recovery_pct,
        transmissivity_m2day=T,
        estimated_yield_m3day=estimated_yield_m3day,
        flowrate_m3day=flowrate_m3day
    )