from models import ConstantRateResult, RecoveryResult, StepDrawdownResult

def _transmissivity_class(T: float) -> str:
    if T < 1:
        return "very low (T < 1 m²/day) — likely suitable for hand pumps only"
    elif T < 10:
        return "low to moderate (1–10 m²/day) — may support limited community supply"
    elif T < 100:
        return "moderate to high (10–100 m²/day) — suitable for motorised community supply"
    else:
        return "high (> 100 m²/day) — suitable for large-scale or mechanised supply"

def _fit_quality(r2: float) -> str:
    if r2 >= 0.95:
        return f"good (R² = {r2:.3f})"
    elif r2 >= 0.85:
        return f"acceptable (R² = {r2:.3f}) — results should be treated with caution"
    else:
        return f"poor (R² = {r2:.3f}) — the straight-line assumption may not hold; consider adjusting the fit window or reviewing the data"

def interpret_constant_rate(result: ConstantRateResult, borehole_name: str = "") -> str:
    name = f"Borehole {borehole_name}" if borehole_name else "The borehole"
    has_fit2 = result.fit2 is not None

    # Primary fit paragraph
    text = (
        f"{name} has an estimated transmissivity of **{result.transmissivity_m2day:.1f} m²/day** "
        f"(Fit 1), indicating {_transmissivity_class(result.transmissivity_m2day)} "
        f"(MacDonald et al., 2005). "
        f"The estimated sustainable yield is approximately "
        f"**{result.estimated_yield_m3day:.0f} m³/day** "
        f"({result.estimated_yield_m3day / 24:.1f} m³/h). "
        f"The Cooper-Jacob straight-line fit quality is "
        f"{_fit_quality(result.fit.r_squared)}."
    )

    # Second fit paragraph — only if present
    if has_fit2:
        agree = abs(result.transmissivity_m2day - result.transmissivity2_m2day)
        ratio = max(result.transmissivity_m2day, result.transmissivity2_m2day) / \
                max(min(result.transmissivity_m2day, result.transmissivity2_m2day), 0.001)

        if ratio < 1.5:
            agreement_note = (
                "The two fits are in **good agreement**, supporting confidence in the result."
            )
        elif ratio < 3.0:
            agreement_note = (
                "The two fits show **moderate divergence** — consider which portion of the "
                "curve better represents steady radial flow conditions."
            )
        else:
            agreement_note = (
                "The two fits show **significant divergence**, suggesting the drawdown curve "
                "may be influenced by boundary effects or non-ideal conditions. "
                "Expert judgement is required to select the most representative result."
            )

        text += (
            f"\n\nA second fit yields a transmissivity of "
            f"**{result.transmissivity2_m2day:.1f} m²/day** (Fit 2), with an estimated "
            f"yield of **{result.estimated_yield2_m3day:.0f} m³/day** "
            f"({result.estimated_yield2_m3day / 24:.1f} m³/h). "
            f"Fit 2 quality is {_fit_quality(result.fit2.r_squared)}. "
            f"{agreement_note}"
        )

    return text

def interpret_recovery(result: RecoveryResult, borehole_name: str = "") -> str:
    T = result.transmissivity_m2day
    name = f"Borehole {borehole_name}" if borehole_name else "The borehole"
    recovery_note = (
        f"The borehole recovered to **{result.recovery_pcg:.1f}%** of static level "
        f"by the end of the monitoring period. "
    )
    if result.recovery_pcg < 80:
        recovery_note += "This incomplete recovery may indicate low aquifer productivity or insufficient recovery time. "
    return (
        f"{name} has an estimated transmissivity of **{T:.1f} m²/day** from recovery analysis, "
        f"indicating {_transmissivity_class(T)}. "
        f"Estimated sustainable yield is approximately **{result.estimated_yield_m3day:.0f} m³/day**. "
        f"{recovery_note}"
        f"The Theis recovery fit quality is {_fit_quality(result.fit.r_squared)}."
    )

def interpret_step_drawdown(result: StepDrawdownResult, borehole_name: str = "") -> str:
    name = f"Borehole {borehole_name}" if borehole_name else "The borehole"
    eff = result.step_results[-1].efficiency_pct if result.step_results else None
    eff_note = ""
    if eff is not None:
        if eff >= 80:
            eff_note = f"Well efficiency at the highest tested rate is **{eff:.0f}%**, indicating well-constructed well with acceptable losses."
        elif eff >= 60:
            eff_note = f"Well efficiency at the highest tested rate is **{eff:.0f}%**, suggesting moderate well losses — screen or gravel pack may warrant review."
        else:
            eff_note = f"Well efficiency at the highest tested rate is only **{eff:.0f}%**, indicating significant non-linear losses — the well construction should be reviewed."

    return (
        f"{name} step-drawdown analysis yields an aquifer loss coefficient "
        f"B = **{result.aquifer_loss_coeff:.4f} m/(m³/h)** and well loss coefficient "
        f"C = **{result.well_loss_coeff:.4f} m/(m³/h)²**. "
        f"The critical yield — where well losses equal aquifer losses — is "
        f"**{result.critical_yield_m3h:.1f} m³/h**; a safe operating rate of "
        f"**{result.critical_yield_m3h * 0.8:.1f} m³/h** (80% of critical) is recommended. "
        f"{eff_note} "
        f"Fit quality is {_fit_quality(result.r_squared)}."
    )