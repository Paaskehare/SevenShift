import math
from datetime import date
from typing import Optional

from leasing import danish_tax_values as MotorStyrelsen


# ──────────────────────────────────────────────
# Depreciation model
# ──────────────────────────────────────────────

FUEL_FACTORS = {
    "petrol": 1.00,
    "diesel": 0.96,
    "hybrid": 1.02,
    "phev": 0.98,
    "ev": 0.92,
}

BRAND_FACTORS = {
    "very_strong": 1.05,
    "strong": 1.02,
    "average": 1.00,
    "weak": 0.97,
    "very_weak": 0.94,
}

_ALPHA_1 = 0.018         # per month, months 0–24 (steeper early depreciation)
_ALPHA_2 = 0.009         # per month, months 24+
_BETA_OVER = 0.0000030   # penalty per km above expected mileage
_BETA_UNDER = 0.0000010  # bonus per km below expected mileage
_EXPECTED_KM_PER_MONTH = 1250  # 15,000 km / year

# Default CO2 estimates (g/km) used when no measured value is available
_DEFAULT_CO2 = {
    "petrol": 130,
    "diesel": 150,
    "hybrid": 49,
    "phev": 49,
    "ev": 0,
}


def _depreciation_factor(age_months: int, mileage_km: int) -> float:
    a1 = min(age_months, 24)
    a2 = max(age_months - 24, 0)
    age_component = _ALPHA_1 * a1 + _ALPHA_2 * a2

    delta_km = mileage_km - _EXPECTED_KM_PER_MONTH * age_months
    beta = _BETA_OVER if delta_km > 0 else _BETA_UNDER
    mileage_component = beta * delta_km

    return max(math.exp(-(age_component + mileage_component)), 0.25)


def _engine_factor(fuel_type: str, engine_liters: Optional[float]) -> float:
    if fuel_type.lower() == "ev" or engine_liters is None:
        return 1.00
    if engine_liters < 1.2:
        return 0.97
    if engine_liters < 1.6:
        return 1.02
    if engine_liters < 2.0:
        return 1.00
    if engine_liters < 3.0:
        return 0.95
    return 0.90


def _residual_factor(
    age_months: int,
    mileage_km: int,
    fuel_type: str,
    brand_strength: str,
    engine_liters: Optional[float],
) -> float:
    F = FUEL_FACTORS.get(fuel_type.lower(), 1.00)
    B = BRAND_FACTORS.get(brand_strength.lower(), 1.00)
    E = _engine_factor(fuel_type, engine_liters)
    return _depreciation_factor(age_months, mileage_km) * F * B * E


def estimate_used_car_value(
    price_today: float,
    age_months: int,
    mileage_km: int,
    fuel_type: str = "petrol",
    brand_strength: str = "average",
    engine_liters: Optional[float] = None,
) -> float:
    """
    Estimate used car market value with piecewise age depreciation (0-24 months vs 24+),
    mileage adjustment, and optional engine-size factor.

    Parameters:
        price_today (float): Current market price (DKK)
        age_months (int): Age of car in months
        mileage_km (int): Current mileage in km
        fuel_type (str): petrol, diesel, hybrid, phev, ev
        brand_strength (str): very_strong, strong, average, weak, very_weak
        engine_liters (float|None): Engine displacement; None for EVs or unknown

    Returns:
        float: Estimated market value (DKK)
    """
    residual = _residual_factor(age_months, mileage_km, fuel_type, brand_strength, engine_liters)
    return round(price_today * residual, 0)


# ──────────────────────────────────────────────
# Danish registration tax (registreringsafgift)
# ──────────────────────────────────────────────

def _get_co2_emission_fee(emission: float, effective_date: date) -> list[float]:
    _, first_limit, first_rate, second_limit, second_rate, _, third_rate = (
        MotorStyrelsen.get_latest_date_row(MotorStyrelsen.CO2_EMISSION_FEE_BRACKETS, effective_date)
    )
    step1 = first_limit * first_rate if emission > first_limit else emission * first_rate
    step2 = (
        (second_limit - first_limit) * second_rate
        if emission > second_limit
        else max((emission - first_limit) * second_rate, 0)
    )
    step3 = (emission - second_limit) * third_rate if emission > second_limit else 0
    return [step1, step2, step3]


def _get_tax_brackets(taxable_value: float, effective_date: date) -> list[float]:
    _, first_limit, first_rate, second_limit, second_rate, _, third_rate = (
        MotorStyrelsen.get_latest_date_row(MotorStyrelsen.TAX_VALUE_BRACKETS, effective_date)
    )
    step1 = first_limit * first_rate if taxable_value > first_limit else taxable_value * first_rate
    step2 = (
        (second_limit - first_limit) * second_rate
        if taxable_value > second_limit
        else max((taxable_value - first_limit) * second_rate, 0)
    )
    step3 = (taxable_value - second_limit) * third_rate if taxable_value > second_limit else 0
    return [step1, step2, step3]


def _get_battery_deduction(battery_capacity_kwh: float, effective_date: date) -> float:
    row = MotorStyrelsen.get_latest_date_row(MotorStyrelsen.BATTERY_DEDUCTIONS, effective_date)
    _, dkk_per_kwh, _, max_kwh = row
    capacity = min(battery_capacity_kwh, max_kwh)
    return capacity * dkk_per_kwh  # negative = deduction


def _get_emission_deductions(emission: float, effective_date: date) -> tuple[float, float, float]:
    _, std_ded, low_limit, low_ded, no_limit, no_ded = (
        MotorStyrelsen.get_latest_date_row(MotorStyrelsen.CO2_LOW_EMISSION_DEDUCTIONS, effective_date)
    )
    return (
        std_ded,
        low_ded if emission < low_limit else 0.0,
        no_ded if emission <= no_limit else 0.0,
    )


def _get_gradual_application_pct(emission: float, effective_date: date) -> float:
    _, first_limit, first_rate, second_limit, second_rate = (
        MotorStyrelsen.get_latest_date_row(MotorStyrelsen.GRADUAL_REGISTRATION_FEE_APPLICATION_BRACKETS, effective_date)
    )
    if emission <= first_limit:
        return first_rate
    if emission < second_limit:
        return second_rate
    return 1.0


def estimate_dk_car_prices(
    used_car_price_dkk: float,
    age_months: int,
    mileage_km: int,
    fuel_type: str = "petrol",
    brand_strength: str = "average",
    engine_liters: Optional[float] = None,
    co2_g_per_km: Optional[float] = None,
    battery_capacity_kwh: float = 0.0,
    effective_date: Optional[date] = None,
) -> dict:
    """
    Estimate the Danish new and used car retail prices, including the full
    registration tax calculation (registreringsafgift) per SKAT rules.

    The used_car_price_dkk is the taxable value of the used car — the market
    price in DKK including Danish VAT but *excluding* residual registration tax.
    This corresponds to the raw vehicle value (steel price) as seen on e.g. mobile.de
    converted to DKK with VAT added.

    Parameters:
        used_car_price_dkk (float): Used car taxable value in DKK (inc VAT, exc reg tax)
        age_months (int): Age of car in months
        mileage_km (int): Current mileage in km
        fuel_type (str): petrol, diesel, hybrid, phev, ev
        brand_strength (str): very_strong, strong, average, weak, very_weak
        engine_liters (float|None): Engine displacement in litres; None for EV or unknown
        co2_g_per_km (float|None): WLTP/NEDC CO2 in g/km; uses fuel-type default if None
        battery_capacity_kwh (float): Battery capacity for EV/PHEV/hybrid deduction
        effective_date (date|None): Date for SKAT bracket selection; defaults to today

    Returns dict with:
        new_taxable_value        – estimated new-car taxable value (exc reg tax)
        new_registration_tax     – estimated new-car registration tax
        new_retail_price         – estimated new-car retail price (taxable + reg tax)
        used_retail_price        – estimated used-car retail price (handelspris)
        used_registration_tax    – estimated residual registration tax
        residual_pct             – value-retention factor used for tax scaling
        co2_g_per_km             – CO2 emission used in calculation
        tax_breakdown            – dict of intermediate tax components
    """
    if effective_date is None:
        effective_date = date.today()

    emission = co2_g_per_km if co2_g_per_km is not None else _DEFAULT_CO2.get(fuel_type.lower(), 130)

    # ── Depreciation / appreciation ──────────────────────────────────────────
    residual = _residual_factor(age_months, mileage_km, fuel_type, brand_strength, engine_liters)
    appreciation = 1.0 / residual

    # ── New car taxable value ────────────────────────────────────────────────
    new_taxable_value = used_car_price_dkk * appreciation

    # Battery deduction on new car (negative = reduces taxable basis)
    battery_ded = _get_battery_deduction(battery_capacity_kwh, effective_date) if battery_capacity_kwh else 0.0
    new_taxable_after_battery = new_taxable_value + battery_ded

    # ── Registration tax brackets ────────────────────────────────────────────
    tax_brackets = _get_tax_brackets(new_taxable_after_battery, effective_date)
    gross_reg_tax = sum(tax_brackets)

    # CO2 emission fee
    co2_fee_parts = _get_co2_emission_fee(emission, effective_date)
    co2_fee = sum(co2_fee_parts)

    reg_tax_after_co2 = gross_reg_tax + co2_fee

    # Emission deductions (bundfradrag + low/no-emission fradrag)
    std_ded, low_ded, no_ded = _get_emission_deductions(emission, effective_date)
    reg_tax_before_gradual = reg_tax_after_co2 + std_ded  # std_ded is negative

    # Gradual application (indfasning) for low/no-emission vehicles
    gradual_pct = _get_gradual_application_pct(emission, effective_date)
    reg_tax_after_gradual = reg_tax_before_gradual * gradual_pct

    new_registration_tax = max(
        reg_tax_after_gradual + low_ded + no_ded,
        MotorStyrelsen.MINIMUM_REGISTRATION_FEE,
    )

    # ── New car retail price ─────────────────────────────────────────────────
    new_retail_price = new_taxable_value + new_registration_tax

    # ── Used car retail price (depreciate new price back) ───────────────────
    used_retail_price_raw = new_retail_price * residual

    # Sales deductions (reklameomkostninger + klargøring)
    advert_ded = used_retail_price_raw * MotorStyrelsen.SALES_ADVERT_DEDUCTION_PCT
    prep_base = (used_retail_price_raw + advert_ded) * MotorStyrelsen.SALES_PREPARATION_DEDUCTION_PCT
    prep_ded = max(prep_base, MotorStyrelsen.SALES_PREPARATION_DEDUCTION_LIMIT)

    used_market_price = used_retail_price_raw + advert_ded + prep_ded

    # ── Value-retention ratio for tax scaling ────────────────────────────────
    # Apply depreciation minimum rule: treat as new if age < 48 months AND mileage < 2000 km
    if age_months == 0:
        pct = 1.0
    elif age_months <= MotorStyrelsen.DEPRECIATION_MINIMUM_IN_MONTHS and mileage_km <= MotorStyrelsen.DEPRECIATION_MINIMUM_IN_KM:
        pct = 1.0
    else:
        pct = used_market_price / new_retail_price

    # ── Used car registration tax ────────────────────────────────────────────
    used_registration_tax = max(
        new_registration_tax * pct,
        MotorStyrelsen.MINIMUM_REGISTRATION_FEE,
    )

    return {
        "new_taxable_value": round(new_taxable_value, 0),
        "new_registration_tax": round(new_registration_tax, 0),
        "new_retail_price": round(new_retail_price, 0),
        "used_retail_price": round(used_retail_price_raw, 0),
        "used_registration_tax": round(used_registration_tax, 0),
        "residual_pct": round(pct, 4),
        "co2_g_per_km": emission,
        "tax_breakdown": {
            "battery_deduction": round(battery_ded, 0),
            "gross_reg_tax": round(gross_reg_tax, 0),
            "co2_fee": round(co2_fee, 0),
            "standard_deduction": round(std_ded, 0),
            "low_emission_deduction": round(low_ded, 0),
            "no_emission_deduction": round(no_ded, 0),
            "gradual_application_pct": gradual_pct,
        },
    }


def estimate_new_car_price(
    current_price: float,
    age_months: int,
    mileage_km: int,
    fuel_type: str = "petrol",
    brand_strength: str = "average",
    engine_liters: Optional[float] = None,
) -> float:
    """
    Fuzzy-estimate the original new-car taxable value by reversing the depreciation model.

    current_price should be the used car taxable value in DKK (exc registration tax).

    Returns:
        float: Estimated new-car taxable value (DKK)
    """
    residual = _residual_factor(age_months, mileage_km, fuel_type, brand_strength, engine_liters)
    return round(current_price / residual, 0)
