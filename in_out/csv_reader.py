import pandas as pd
from pathlib import Path
from models import PumpingTest, Borehole, Measurement, Step, TestType
from typing import Optional
from datetime import date

REQUIRED_COLUMNS = {"time_min", "level_mbd"}
MIN_ROWS = 3  # absolute floor — not meaningful below this

def _load_and_validate_csv(path: str | Path) -> pd.DataFrame:
    """
    Load CSV file and perform file and column level checks.
    Returns a clean DataFrame with time_min and level_mbd columns.
    This is shared by all test types.
    """
    path = Path(path)
    try:
        df = pd.read_csv(path)
    except Exception as e:
        raise ValueError(f"Error reading CSV file '{path}': {e}")
    
    # Check if file is empty
    if df.empty:
        raise ValueError("CSV file is empty. Please provide a file with data.")
    
    # Check for encoding issues or wrong delimiters (e.g., semicolons instead of commas)
    if df.shape[1] < 2:
        raise ValueError(
            f"CSV file has {df.shape[1]} column(s). Expected at least 2 columns: {REQUIRED_COLUMNS}. "
            "Check for encoding issues or wrong delimiters (e.g., semicolons instead of commas)."    
        )

    # Check for required columns presence and typos
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(
            f"Missing required column(s): {missing}. "
            f"Found: {list(df.columns)}."
        )
    
    # Check for data types
    for col in REQUIRED_COLUMNS:
        if not pd.api.types.is_numeric_dtype(df[col]):
            non_numeric = df[col][pd.to_numeric(df[col], errors='coerce').isna()]
            raise ValueError(
                f"Column '{col}' must be numeric. "
                f"Found non-numeric value(s): {non_numeric.tolist()}"
            )
    
    # Check for missing values in required columns
    if df[list(REQUIRED_COLUMNS)].isnull().any().any():
        raise ValueError(f"Missing values in required columns {REQUIRED_COLUMNS}. Check CSV for incomplete data.")
    
    # Check for minimum number of rows
    if len(df) < MIN_ROWS:
        raise ValueError(
            f"CSV contains only {len(df)} row(s). "
            f"At least {MIN_ROWS} measurements are required."
        )
    
    return df[list(REQUIRED_COLUMNS)].copy()

def _validate_time_series(time: pd.Series) -> None:
    """
    Validate that time values are non-negative, non-duplicate,
    and monotonically increasing.
    """
    if (time < 0).any():
        raise ValueError(f"Negative time value(s) found: {time[time < 0].tolist()}.")
    if time.duplicated().any():
        dupes = time[time.duplicated()].tolist()
        raise ValueError(f"Duplicate time value(s) found: {dupes}.")
    if not time.is_monotonic_increasing:   # this is a property, not a method
        raise ValueError("Time values must be monotonically increasing.")

def read_constant_rate_csv(
    path: str | Path,
    borehole: Borehole,
    flowrate_m3h: float,
    test_date: Optional[date] = None,
    operator: Optional[str] = None
) -> PumpingTest:
    """
    Read a constant-rate pumping test from a CSV file and return a PumpingTest object.
    The CSV file must contain at least the following columns:
        - time_min: Elapsed time in minutes since the start of the test
        - level_mbd: Water level in meters below datum (mbd)
    """
    df = _load_and_validate_csv(path)
    _validate_time_series(df["time_min"])

    measurements = [
        Measurement(time_min=float(row.time_min), level_mbd=float(row.level_mbd))
        for row in df.itertuples(index=False)
    ]

    return PumpingTest(
        borehole=borehole,
        test_type=TestType.CONSTANT_RATE,
        measurements=measurements,
        test_date=test_date,
        operator=operator,
        flowrate_m3h=flowrate_m3h
    )

def read_recovery_csv(
    path: str | Path,
    borehole: Borehole,
    flowrate_m3h: float,
    end_of_pumping_min: float,
    test_date: Optional[date] = None,
    operator: Optional[str] = None
) -> PumpingTest:
    """
    Read a recovery test from a CSV file and return a PumpingTest object.
    The CSV file must contain at least the following columns:
        - time_min: Elapsed time in minutes since the start of the recovery phase (t')
        - level_mbd: Water level in meters below datum (mbd)
    
    The end_of_pumping_min parameter is the elapsed time at which pumping stopped and recovery started.
    """
    df = _load_and_validate_csv(path)
    _validate_time_series(df["time_min"])

    measurements = [
        Measurement(time_min=float(row.time_min), level_mbd=float(row.level_mbd))
        for row in df.itertuples(index=False)
    ]

    return PumpingTest(
        borehole=borehole,
        test_type=TestType.RECOVERY,
        measurements=measurements,
        test_date=test_date,
        operator=operator,
        flowrate_m3h=flowrate_m3h,
        end_of_pumping_min=end_of_pumping_min
    )

def read_step_drawdown_csv(
    path: str | Path,
    borehole: Borehole,
    steps: list[Step],
    test_date: Optional[date] = None,
    operator: Optional[str] = None
) -> PumpingTest:
    """
    Read a step-drawdown test from a CSV file and return a PumpingTest object.
    The CSV file must contain at least the following columns:
        - time_min: Elapsed time in minutes since the start of the test
        - level_mbd: Water level in meters below datum (mbd)
    The steps parameter is a list of Step objects defining the flowrate and end time of each step.
    """
    df = _load_and_validate_csv(path)
    _validate_time_series(df["time_min"])

    # Check that end_time_min exists in the measurements data
    max_time = df["time_min"].max()
    for step in steps:
        if step.end_time_min > max_time:
            raise ValueError(
                f"Step {step.step_number} end time ({step.end_time_min} min) "
                f"exceeds the maximum time in the CSV ({max_time} min)."
            )
    
    # Check that there's at least one measurement per step
    if len(df) < len(steps):
        raise ValueError(
            f"CSV contains {len(df)} row(s) but {len(steps)} steps are defined. "
            "There must be at least one measurement per step."
        )

    measurements = [
        Measurement(time_min=float(row.time_min), level_mbd=float(row.level_mbd))
        for row in df.itertuples(index=False)
    ]

    return PumpingTest(
        borehole=borehole,
        test_type=TestType.STEP_DRAWDOWN,
        measurements=measurements,
        test_date=test_date,
        operator=operator,
        steps=steps
    )