from dataclasses import dataclass
from typing import Optional
from models import Borehole, PumpingTest, ConstantRateResult, RecoveryResult, StepDrawdownResult, Step
from in_out.csv_reader import read_constant_rate_csv, read_recovery_csv, read_step_drawdown_csv
from analysis.constant_rate import analyse_constant_rate
from analysis.recovery import analyse_recovery
from analysis.step_drawdown import analyse_step_drawdown
from config.schema import BoreholeConfig, ConstantRateConfig, RecoveryConfig, StepDrawdownConfig


@dataclass
class ConstantRateSession:
    test: PumpingTest
    result: ConstantRateResult

@dataclass
class RecoverySession:
    test: PumpingTest
    result: RecoveryResult

@dataclass
class StepDrawdownSession:
    test: PumpingTest
    result: StepDrawdownResult

def run_constant_rate(
    borehole_config: BoreholeConfig,
    cr_config: ConstantRateConfig,
    fit_start: Optional[int] = None,
    fit_end: Optional[int] = None,
    fit2_start: Optional[int] = None,
    fit2_end: Optional[int] = None,
) -> ConstantRateSession:
    """
    Shared orchestration for constant-rate analysis.
    Used by both the CLI and the Shiny app.
    Raises ValueError on invalid input or analysis failure — caller handles presentation.
    """
    borehole = Borehole.minimal(
        name=borehole_config.name,
        static_level_mbd=borehole_config.static_level_mbd,
    )
    resolved_fit_start = fit_start if fit_start is not None else cr_config.fit_start_idx
    resolved_fit_end = fit_end if fit_end is not None else cr_config.fit_end_idx

    test = read_constant_rate_csv(
        path=cr_config.csv_file,
        borehole=borehole,
        flowrate_m3h=cr_config.flowrate_m3h,
    )
    result = analyse_constant_rate(
        test,
        fit_start_idx=resolved_fit_start,
        fit_end_idx=resolved_fit_end,
        fit2_start_idx=fit2_start,
        fit2_end_idx=fit2_end,
    )
    return ConstantRateSession(test=test, result=result)


def run_recovery(
    borehole_config: BoreholeConfig,
    r_config: RecoveryConfig,
    fit_start: Optional[int] = None,
    fit_end: Optional[int] = None,
) -> RecoverySession:
    """
    Shared orchestration for recovery analysis.
    Used by both the CLI and the Shiny app.
    Raises ValueError on invalid input or analysis failure — caller handles presentation.
    """
    borehole = Borehole.minimal(
        name=borehole_config.name,
        static_level_mbd=borehole_config.static_level_mbd,
    )
    resolved_fit_start = fit_start if fit_start is not None else r_config.fit_start_idx
    resolved_fit_end = fit_end if fit_end is not None else r_config.fit_end_idx

    test = read_recovery_csv(
        path=r_config.csv_file,
        borehole=borehole,
        flowrate_m3h=r_config.flowrate_m3h,
        end_of_pumping_min=r_config.end_of_pumping_min
    )
    result = analyse_recovery(
        test,
        fit_start_idx=resolved_fit_start,
        fit_end_idx=resolved_fit_end,
    )
    return RecoverySession(test=test, result=result)


def run_step_drawdown(
    borehole_config: BoreholeConfig,
    sd_config: StepDrawdownConfig,
) -> StepDrawdownSession:
    """
    Shared orchestration for step-drawdown analysis.
    Used by both the CLI and the Shiny app.
    Raises ValueError on invalid input or analysis failure — caller handles presentation.
    """
    borehole = Borehole.minimal(
        name=borehole_config.name,
        static_level_mbd=borehole_config.static_level_mbd
    )
    steps = [
        Step(step_number=i, flowrate_m3h=s.flowrate_m3h, end_time_min=s.end_time_min)
        for i, s in enumerate(sd_config.steps_raw, start=1)
    ]

    test = read_step_drawdown_csv(
        path=sd_config.csv_file,
        borehole=borehole,
        steps=steps
    )
    result = analyse_step_drawdown(
        test
    )
    return StepDrawdownSession(test=test, result=result)