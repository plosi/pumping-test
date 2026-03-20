from dataclasses import dataclass
from typing import Optional
from pathlib import Path
from datetime import date

@dataclass
class BoreholeConfig:
    """
    Borehole configuration as provided by the user.
    Only name and static_level_mbd are required for analysis.
    All other fields are optional and used for record-keeping.
    """
    name: str
    static_level_mbd: float  # Static water level in meters below datum (mbd)
    # The following are not needed for the analysis so we'll keep them as optional
    depth_m: Optional[float] = None  # Total depth of the borehole
    diameter_mm: Optional[float] = None  # Diameter of the casing in mm
    pump_depth_mbd: Optional[float] = None   # Depth of the pump intake below datum in meters
    datum_height_m: Optional[float] = None   # Height of the datum above ground level in meters
    datum_description: Optional[str] = None  # Description of the datum (e.g., top of casing, ground level, etc.)
    location: Optional[str] = None   # Human-readable location name
    gps: Optional[tuple[float, float]] = None  # (latitude, longitude)
    pump_type: Optional[str] = None    # Type and model of pump used for testing

@dataclass
class ConstantRateConfig:
    """ Configuration for a constant rate pumping test. """
    csv_file: Path
    flowrate_m3h: float
    fit_start_idx: int = 1
    fit_end_idx: Optional[int] = None

@dataclass
class RecoveryConfig:
    """ Configuration for a recovery test. """
    csv_file: Path
    flowrate_m3h: float
    end_of_pumping_min: float
    fit_start_idx: int = 1
    fit_end_idx: Optional[int] = None

@dataclass
class StepConfig:
    """ Configuration for a single step in the step-drawdown test. """
    flowrate_m3h: float
    end_time_min: float

@dataclass
class StepDrawdownConfig:
    """ Configuration for a step drawdown test. """
    csv_file: Path
    steps_raw: list[StepConfig]

@dataclass
class BoreholeCampaignConfig:
    """
    Top-level configuration object for a borehole test campaign.
    At least one test section must be present.
    """
    borehole: BoreholeConfig
    test_date: Optional[date] = None
    operator: Optional[str] = None
    constant_rate: Optional[ConstantRateConfig] = None
    recovery: Optional[RecoveryConfig] = None
    step_drawdown: Optional[StepDrawdownConfig] = None