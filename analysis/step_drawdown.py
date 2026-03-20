from models import Step, TestType, PumpingTest, StepDrawdownResult, StepResult
import numpy as np

HOURS_PER_DAY = 24.0

def _get_drawdown_at_end_of_step(
        step: Step,
        time_series: np.ndarray,
        drawdown_series: np.ndarray
) -> float:
    """
    Find the drawdown at the end of the step.
    Uses the closest measurement to step.end_time_min rather
    than an exact match, to handle floating point timestamps.

    Args:
        step: The step whose end-time drawdown we want to find.
        time_series: Full elapsed time array in minutes.
        drawdown_series: Full drawdown array in meters.
    
    Returns:
        Drawdown in meters at the end of the step.
    """
    end_time_idx = np.argmin(np.abs(time_series - step.end_time_min))   # Find index of closest time to step end
    return drawdown_series[end_time_idx]

def _fit_specific_drawdown(
    flowrates: np.ndarray,  # Q values in m3/h
    specific_drawdowns: np.ndarray  # s/Q values in h/m²
) -> tuple[float, float, float]:
    """
    Fit a straight line to the s/Q vs Q plot (Hantush-Bierschenk).

        s/Q = B + C*Q

    Returns:
        (B, C, r_squared)
    """
    # Calculate slope (C) and intercept (B)
    slope, intercept = np.polyfit(flowrates, specific_drawdowns, 1)
    
    # Calculate R² for the fit
    y_pred = slope * flowrates + intercept
    ss_res = np.sum((specific_drawdowns - y_pred) ** 2)
    ss_tot = np.sum((specific_drawdowns - np.mean(specific_drawdowns)) ** 2)
    r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

    return intercept, slope, r_squared

def analyse_step_drawdown(
    test: PumpingTest
) -> StepDrawdownResult:
    """
    Analyse a step-drawdown test using the Hantush-Bierschenk method.

    Fits the equation s/Q = B + C*Q to extract aquifer (B) and well (C)
    loss coefficients. Per-step efficiency is computed as:
        efficiency = BQ / (BQ + CQ²) * 100

    Args:
        test: A PumpingTest with test_type == STEP_DRAWDOWN and
              at least 2 steps defined.

    Returns:
        StepDrawdownResult with B, C, and per-step breakdown.

    Raises:
        ValueError: If test type is wrong, fewer than 2 steps, steps are
                    not sorted, or drawdown is non-positive for any step.

    Reference:
        ICRC (2011), Technical Review, Section 4 / Hantush & Bierschenk (1964)
    """
    # Validate test type
    if test.test_type != TestType.STEP_DRAWDOWN:
        raise ValueError(f"Expected test type step_drawdown, got {test.test_type}.")
    
    # Check steps are sorted by end_time_min
    steps = test.steps
    if not all(steps[i].end_time_min < steps[i+1].end_time_min for i in range(len(steps)-1)):
        raise ValueError("Steps must be sorted in ascending order of end_time_min.")
    
    # Check if flowrates are increasing
    flowrates = np.array([s.flowrate_m3h for s in steps])
    if not np.all(np.diff(flowrates) > 0):
        raise ValueError("Flowrates must be increasing across steps.")
    
    # Get drawdown at the end of each step
    time_series = test.time_series
    drawdown_series = test.drawdown_series

    drawdowns = [
        _get_drawdown_at_end_of_step(step, time_series, drawdown_series)
        for step in steps
    ]

    # Calculate specific drawdown (s/Q) for each step
    drawdown_arr = np.array(drawdowns)
    # Check for non-positive drawdown values which would invalidate the analysis
    if np.any(drawdown_arr <= 0):
        bad_steps = [s.step_number for s, d in zip(steps, drawdowns) if d <= 0]
        raise ValueError(
            f"Non-positive drawdown detected at step(s) {bad_steps}. "
            "Check static level and measurements."
        )
    specific_drawdowns = drawdown_arr / flowrates  # s/Q in h/m²

    # Fit s/Q vs Q to get B and C
    B, C, r_squared = _fit_specific_drawdown(flowrates, specific_drawdowns)

    # Calculate critical yield where the linear and non-linear losses are equal: BQ = CQ² => Q_crit = B/C
    # At Q_crit, linear and non-linear losses are equal: BQ = CQ² → Q_crit = B/C
    # Operating above Q_crit means well losses dominate — generally undesirable
    # This will allow to calculate the safe yield, usually 75-80% of the critical yield
    critical_yield_m3h = B / C if C !=0 else float("inf")

    # Calculate per-step results
    step_results = []
    for step, s, sd in zip(steps, drawdowns, specific_drawdowns):
        linear_loss = B * step.flowrate_m3h
        nonlinear_loss = C * step.flowrate_m3h ** 2
        efficiency = (linear_loss / (linear_loss + nonlinear_loss)) * 100 if (linear_loss + nonlinear_loss) > 0 else 0.0
        flowrate_m3day = step.flowrate_m3h * HOURS_PER_DAY
        step_results.append(
            StepResult(
                step=step,
                drawdown_m=s,
                specific_drawdown_hm2=sd,
                specific_capacity_m2d=flowrate_m3day / s,
                linear_loss_m=linear_loss,
                nonlinear_loss_m=nonlinear_loss,
                efficiency_pct=efficiency
            )
        )
    
    return StepDrawdownResult(
        aquifer_loss_coeff=B,
        well_loss_coeff=C,
        critical_yield_m3h=critical_yield_m3h,
        r_squared=r_squared,
        step_results=step_results
    )
