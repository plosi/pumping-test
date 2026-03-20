# from loader import load_config_file
from .schema import BoreholeCampaignConfig, BoreholeConfig, ConstantRateConfig, RecoveryConfig, StepConfig, StepDrawdownConfig
from pathlib import Path
from datetime import date
from typing import Optional, Any

def _parse_date(value, section: str) -> date:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            raise ValueError(
                f"Invalid date format in '{section}': '{value}'. "
                "Expected ISO format: YYYY-MM-DD."
            )
    raise ValueError(f"'{section}.test_date' must be a date string, got {type(value).__name__}.")

def _valid_field(raw: dict, key: str, expected_type: type, section: str, optional: bool = False) -> Any:
    """
    Assert a key exists in raw and is of the expected type.
    A section is used in error messages to tell the user where the problem is.
    
    Raises ValueError with a clear message if either check fails.
    """
    if optional and key not in raw:
        return None
    
    if key not in raw:
        raise ValueError(
            f"Missing required field '{key}' in '{section}' section."
        )
    if not isinstance(raw[key], expected_type):
        type_name = (
            " or ".join(t.__name__ for t in expected_type)
            if isinstance(expected_type, tuple)
            else expected_type.__name__
        )
        raise ValueError(
            f"'{section}.{key}' must be of type {type_name}, "
            f"got {type(raw[key]).__name__}."
        )
    return raw[key]


def _valid_number(raw: dict, key: str, section: str, positive: bool = False, optional: bool = False) -> Optional[float]:
    """ Validate any number into float. """
    if optional and key not in raw:
        return None
    
    value = float(_valid_field(raw, key, (int, float), section, optional=optional))
    if positive and value <= 0:
        raise ValueError(
            f"'{section}.{key}' must be positive, got {value}."
        )
    return value

def _validate_borehole(raw: dict) -> BoreholeConfig:
    """Validates the 'borehole' section."""
    section = "borehole"
    name = _valid_field(raw, "name", str, section)
    static_level = _valid_number(raw, "static_level_mbd", section, positive=True)
    depth = _valid_number(raw, "depth_m", section, positive=True, optional=True)
    diameter = _valid_number(raw, "diameter_mm", section, positive=True, optional=True)
    pump_depth = _valid_number(raw, "pump_depth_mbd", section, positive=True, optional=True)
    datum_height = _valid_number(raw, "datum_height_m", section, positive=True, optional=True)
    datum_description = _valid_field(raw, "datum_description", str, section, optional=True)
    location = _valid_field(raw, "location", str, section, optional=True)
    pump_type = _valid_field(raw, "pump_type", str, section, optional=True)

    gps_raw = _valid_field(raw, "gps", list, section, optional=True)
    gps = None
    if gps_raw is not None:
        if len(gps_raw) != 2:
            raise ValueError(
                f"'borehole.gps' must have exactly 2 values [latitude, longitude], "
                f"got {len(gps_raw)}."
            )
        if not all(isinstance(v, (int, float)) for v in gps_raw):
            raise ValueError(
                f"'borehole.gps' values must be numbers, got {gps_raw}."
            )
        gps = (float(gps_raw[0]), float(gps_raw[1]))
    if gps[0] not in range(-90, 90):
        raise ValueError("Latitude values must be between -90 and 90.")
    if gps[1] not in range(-180, 180):
        raise ValueError("Longitude values must be between -180 and 180.")

    return BoreholeConfig(
        name=name,
        static_level_mbd=static_level,
        depth_m=depth,
        diameter_mm=diameter,
        pump_depth_mbd=pump_depth,
        datum_height_m=datum_height,
        datum_description=datum_description,
        location=location,
        gps=gps,
        pump_type=pump_type
    )

def _validate_csv_path(raw: dict, section: str, config_dir: Path) -> Path:
    """Read csv_file from raw, resolve relative to config_dir, check it exists."""
    csv_str = _valid_field(raw, "csv_file", str, section)
    csv_path = (config_dir / csv_str).resolve()
    if not csv_path.exists():
        raise ValueError(
            f"'{section}.csv_file' points to a file that does not exist: '{csv_path}'."
        )
    return csv_path

def _validate_constant_rate(raw: dict, config_dir: Path) -> ConstantRateConfig:
    """Validates the 'constant_rate' section."""
    section = "constant_rate"
    raw = raw[section]
    csv_file = _validate_csv_path(raw, section, config_dir)
    
    flowrate = _valid_number(raw, "flowrate_m3h", section, positive=True)
    fit_start = _valid_field(raw, "fit_start_idx", int, section, optional=True) or 1
    fit_end = _valid_field(raw, "fit_end_idx", int, section, optional=True)

    return ConstantRateConfig(
        csv_file=csv_file,
        flowrate_m3h=flowrate,
        fit_start_idx=fit_start,
        fit_end_idx=fit_end
    )

def _validate_recovery(raw: dict, config_dir: Path) -> RecoveryConfig:
    """Validates the 'recovery' section."""
    section = "recovery"
    raw = raw[section]
    csv_file = _validate_csv_path(raw, section, config_dir)
    
    flowrate = _valid_number(raw, "flowrate_m3h", section, positive=True)
    end_of_pumping = _valid_number(raw, "end_of_pumping_min", section, positive=True)
    fit_start = _valid_field(raw, "fit_start_idx", int, section, optional=True) or 1
    fit_end = _valid_field(raw, "fit_end_idx", int, section, optional=True)

    return RecoveryConfig(
        csv_file=csv_file,
        flowrate_m3h=flowrate,
        end_of_pumping_min=end_of_pumping,
        fit_start_idx=fit_start,
        fit_end_idx=fit_end
    )

def _validate_step(raw: dict, index: int) -> StepConfig:
    """Validates a single step entry."""
    section = f"steps[{index}]"
    flowrate = _valid_number(raw, "flowrate_m3h", section, positive=True)
    end_time = _valid_number(raw, "end_time_min", section, positive=True)

    return StepConfig(
        flowrate_m3h=flowrate,
        end_time_min=end_time
    )

def _validate_step_drawdown(raw: dict, config_dir: Path) -> StepDrawdownConfig:
    """Validates the 'step_drawdown' section."""
    section = "step_drawdown"
    raw = raw[section]
    csv_file = _validate_csv_path(raw, section, config_dir)
    steps_data = _valid_field(raw, "steps", list, section)
    
    if len(steps_data) < 3:
        raise ValueError(
            f"'{section}.steps' must contain at least 3 steps, "
            f"got {len(steps_data)}."
        )

    steps = [_validate_step(s, i) for i, s in enumerate(steps_data, start=1)]

    return StepDrawdownConfig(
        csv_file=csv_file,
        steps_raw=steps
    )

def validate_config(raw: dict, config_path: Path) -> BoreholeCampaignConfig:
    """Entry point. Validates the full config dict."""
    config_dir = config_path.parent

    if "borehole" not in raw:
        raise ValueError("Missing required 'borehole' section in config file.")
    borehole = _validate_borehole(raw["borehole"])

    section = "config"
    date_value = _valid_field(raw, "test_date", (str, date), section, optional=True)
    parsed_date = _parse_date(date_value, section) if date_value is not None else None
    operator = _valid_field(raw, "operator", str, section, optional=True)

    constant_rate = _validate_constant_rate(raw, config_dir) if "constant_rate" in raw else None
    recovery = _validate_recovery(raw, config_dir) if "recovery" in raw else None
    step_drawdown = _validate_step_drawdown(raw, config_dir) if "step_drawdown" in raw else None

    if all(t is None for t in [constant_rate, recovery, step_drawdown]):
        raise ValueError(
            "Config must define at least one test section "
            "('constant_rate', 'recovery', or 'step_drawdown')."
        )

    return BoreholeCampaignConfig(
        borehole=borehole,
        test_date=parsed_date,
        operator=operator,
        constant_rate=constant_rate,
        recovery=recovery,
        step_drawdown=step_drawdown
    )