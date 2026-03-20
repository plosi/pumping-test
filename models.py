from enum import Enum
from dataclasses import dataclass, field
from typing import Optional
import numpy as np
from datetime import date


# ----------------------------
# Enums
# ----------------------------

class TestType(Enum):
    """ The tree single-well test types referenced by the ICRC 2011 guidelines."""
    STEP_DRAWDOWN = "step_drawdown"
    CONSTANT_RATE = "constant_rate"
    RECOVERY = "recovery"

# ----------------------------
# Core domain objects
# ----------------------------

@dataclass
class Borehole:
    """
    Physiscal properties of the borehole being tested.
    All depth/level measurements are in meters below the datum (mbd)
    unless otherwise specified.
    """
    name: str
    depth_m: float  # Total depth of the borehole
    diameter_mm: float  # Diameter of the casing in mm
    static_level_mbd: float  # Static water level in meters below datum (mbd)
    pump_depth_mbd: float   # Depth of the pump intake below datum in meters
    datum_height_m: float   # Height of the datum above ground level in meters
    datum_description: str  # Description of the datum (e.g., top of casing, ground level, etc.)
    location: Optional[str] = None   # Human-readable location name
    gps: Optional[tuple[float, float]] = None  # (latitude, longitude)
    pump_type: Optional[str] = None    # Type and model of pump used for testing

    def __post_init__(self):
        if self.depth_m <= 0:
            raise ValueError(f"Borehole depth must be positive, got {self.depth_m}.")
        if self.diameter_mm < 70:
            raise ValueError(f"Diameter {self.diameter_mm} mm is below the minimum of 70 mm.")
        if self.static_level_mbd < 0:
            raise ValueError(f"Static level cannot be negative, got {self.static_level_mbd}.")
        if self.pump_depth_mbd < 0 or self.pump_depth_mbd > self.depth_m:
            raise ValueError(f"Pump depth must be a positive value not exceeding borehole depth, got {self.pump_depth_mbd}.")

    @classmethod
    def minimal(cls, name: str, static_level_mbd: float) -> "Borehole":
        """Create a Borehole with only the fields required for analysis."""
        return cls(
            name=name,
            static_level_mbd=static_level_mbd,
            depth_m=999.0,
            diameter_mm=200.0,
            pump_depth_mbd=50.0,
            datum_height_m=0.7,
            datum_description="Not specified",
        )

@dataclass
class Measurement:
    """
    Single measurement of water level and (optionally) physico-chemical parameters
    at specified time intervals during a test.
    
    Water level is stored as measured in meters from datum (mbd).
    Temperature is stored in degrees Celsius, pH is unitless, turbidity in NTU,
    and conductivity in µS/cm.

    Drawdown is computed on demand relative to the borehole's static level.
    """
    time_min: float # Elapsed time since the start of the test in minutes
    level_mbd: float  # Measured water level in meters below datum (mbd)
    temperature_c: Optional[float] = None  # Temperature in degrees Celsius
    ph: Optional[float] = None  # pH value (unitless)
    turbidity_ntu: Optional[float] = None    # Turbidity in NTU
    conductivity_us_cm: Optional[float] = None  # Conductivity in µS/cm

    def __post_init__(self):
        if self.time_min < 0:
            raise ValueError(f"Time cannot be negative, got {self.time_min}.")
        if self.level_mbd < 0:
            raise ValueError(f"Water level cannot be negative, got {self.level_mbd}.")
        if self.temperature_c is not None and (self.temperature_c < -50 or self.temperature_c > 150):
            raise ValueError(f"Temperature {self.temperature_c} °C is out of realistic range.")
        if self.ph is not None and (self.ph < 0 or self.ph > 14):
            raise ValueError(f"pH value {self.ph} is out of valid range (0-14).")
        if self.turbidity_ntu is not None and self.turbidity_ntu < 0:
            raise ValueError(f"Turbidity cannot be negative, got {self.turbidity_ntu}.")
        if self.conductivity_us_cm is not None and self.conductivity_us_cm < 0:
            raise ValueError(f"Conductivity cannot be negative, got {self.conductivity_us_cm}.")
    
    def drawdown(self, static_level_mbd: float) -> float:
        """ Calculate drawdown relative to the static water level."""
        return self.level_mbd - static_level_mbd

@dataclass
class Step:
    """ Represents a single step in a step-drawdown test. """
    step_number: int    # Sequential number of the step, starting from 1
    flowrate_m3h: float # Pumping rate for this step in m3/h
    end_time_min: float # Elapsed time at the end of this step in minutes

    def __post_init__(self):
        if self.step_number < 1:
            raise ValueError(f"Step number must be a positive integer, got {self.step_number}.")
        if self.flowrate_m3h <= 0:
            raise ValueError(f"Flowrate must be positive, got {self.flowrate_m3h}.")
        if self.end_time_min <= 0:
            raise ValueError(f"End time must be positive, got {self.end_time_min}.")
        
# ----------------------------
# Pumping test configurations
# ----------------------------

@dataclass
class PumpingTest:
    """
    A complete pumping test: the borehole, test type, raw measurements,
    and test-specific parameters.

    This is the central object passed to analysis functions.
    """
    borehole: Borehole
    test_type: TestType
    measurements: list[Measurement]
    test_date: Optional[date] = None # ISO format date of the test (YYYY-MM-DD)
    operator: Optional[str] = None  # Name of the person conducting the test

    # Step-drawdown specific parameters
    steps: list[Step] = field(default_factory=list)

    # Constant rate / recovery specific parameters - stated as optional here for readability
    # but they are actually required and it will raise error if missing
    flowrate_m3h: Optional[float] = None # Average pumping rate
    end_of_pumping_min: Optional[float] = None   # Elapsed time at the end of pumping phase (start of recovery) in minutes

    def __post_init__(self):
        if not self.measurements:
            raise ValueError("A pumping test must have at least one measurement.")
        self._validate_for_test_type()
    
    def _validate_for_test_type(self):
        if self.test_type == TestType.STEP_DRAWDOWN:
            if len(self.steps) < 3:
                raise ValueError("Step-drawdown tests must have at least 3 steps defined.")
        elif self.test_type == TestType.CONSTANT_RATE:
            if self.flowrate_m3h is None or self.flowrate_m3h <= 0:
                raise ValueError(f"Constant rate tests must have a positive flowrate, got {self.flowrate_m3h}.")
        elif self.test_type == TestType.RECOVERY:
            if self.end_of_pumping_min is None or self.end_of_pumping_min <= 0:
                raise ValueError(f"Recovery tests must have a positive end of pumping time, got {self.end_of_pumping_min}.")
            if self.flowrate_m3h is None or self.flowrate_m3h <= 0:
                raise ValueError(f"Recovery tests must have a positive flowrate for the pumping phase, got {self.flowrate_m3h}.")
    
    @property
    def time_series(self) -> np.ndarray:
        """ Elapsed time as a numpy array in minutes."""
        return np.array([m.time_min for m in self.measurements])
    
    @property
    def level_series(self) -> np.ndarray:
        """ Measured water levels as a numpy array in meters below datum (mbd)."""
        return np.array([m.level_mbd for m in self.measurements])
    
    @property
    def drawdown_series(self) -> np.ndarray:
        """ Drawdown series calculated from measurements and borehole static level. """
        sl = self.borehole.static_level_mbd
        return np.array([m.drawdown(sl) for m in self.measurements])

# ----------------------------
# Results objects
# ----------------------------

@dataclass
class DrawdownFit:
    """
    Result of fitting a straight line to the semi-log drawdown curve.
    Used by both constant-rate and recovery analysis.

    The fit equation is: s = slope * ln(t) + intercept
    ds (drawdown per log cycle) is derived from the slope over one log cycle.

    Reference: ICRC (2011), Section 4.2
    """
    slope: float    # m in s = m*ln(t) + c
    intercept: float    # c
    drawdown_per_log_cycle: float   # ds over one log cycle [m]
    n_points_used: int  # how many points were included in the fit
    r_squared: float    # R² value of the fit, indicating goodness of fit

@dataclass
class StepResult:
    """
    Results from analyzong a single step in a step-drawdown
    """
    step: Step
    drawdown_m: float
    specific_drawdown_hm2: float   # s/Q [h/m²]
    specific_capacity_m2d: float   # Q/s [m²/d]
    linear_loss_m: float           # BQ
    nonlinear_loss_m: float        # CQ²
    efficiency_pct: float          # BQ / (BQ + CQ²) * 100

@dataclass
class StepDrawdownResult:
    """ Results from analyzing a step-drawdown test. """
    aquifer_loss_coeff: float  # linear (acquifer) loss coefficient [m/(m3/h)]
    well_loss_coeff: float  # non-linear (well) loss coefficient [m/(m3/h)^2]
    critical_yield_m3h: float   # Flowrate at which linear and non-linear losses are equal [m3/h]
    r_squared: float    # R² of the B-C fit
    step_results: list[StepResult]    # Data for each step: Hantush-Bierschenk calculations, specific drawdown, etc.

    def specific_drawdown_at(self, flowrate_m3h: float) -> float:
        """ Calculate specific drawdown at given flowrate """
        return self.aquifer_loss_coeff + self.well_loss_coeff * flowrate_m3h

@dataclass
class ConstantRateResult:
    """Results of a constant-rate test analysis (Cooper-Jacob method)."""
    fit: DrawdownFit
    transmissivity_m2day: float    # T [m²/day]
    estimated_yield_m3day: float   # based on MacDonald et al. (2005)
    flowrate_m3day: float          # Q used in analysis [m³/day]

@dataclass
class RecoveryResult:
    """Results of a recovery test analysis (Theis recovery method)."""
    fit: DrawdownFit
    recovery_pcg: float
    transmissivity_m2day: float
    estimated_yield_m3day: float
    flowrate_m3day: float