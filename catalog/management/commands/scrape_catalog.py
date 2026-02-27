"""
Management command: scrape_catalog

Imports car specifications from auto-data.net into the catalog.

API hierarchy
─────────────
  brands.php    (GET)               → list of {id, na}
  models.php    (POST, id=brand_id) → list of {id, na}
  submodels.php (POST, id=model_id) → list of {id, na}
  listcars.php  (POST, id=sub_id)   → numbered dict: {"0": {v1, id}, …}
  showcar.php   (POST, id=car_id)   → numbered dict: {"0": {t}, "1": {p, v}, …}

All responses are double-base64 encoded JSON; _decode() handles that.
"""

import base64
import json
import logging
import re
import time

import requests
from django.core.management.base import BaseCommand
from django.utils import timezone

from catalog.models import Make, CarModel, Generation, Variant

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# API client
# ---------------------------------------------------------------------------

class AutoDataClient:
    BASE_URL = 'https://vps2.auto-data.net/app/'
    LANG = 'en'

    def __init__(self):
        requests.packages.urllib3.disable_warnings(
            requests.packages.urllib3.exceptions.InsecureRequestWarning
        )
        self.session = requests.Session()
        self.session.verify = False  # auto-data.net has certificate quirks

    @staticmethod
    def _decode(raw: str):
        s1 = base64.b64decode(raw[17:])
        s2 = base64.b64decode(s1[14:])
        return json.loads(s2)

    def _get(self, endpoint, **params):
        params['lang'] = self.LANG
        resp = self.session.get(self.BASE_URL + endpoint, params=params, timeout=15)
        resp.raise_for_status()
        return self._decode(resp.text)

    def _post(self, endpoint, **payload):
        payload['lang'] = self.LANG
        resp = self.session.post(self.BASE_URL + endpoint, data=payload, timeout=15)
        resp.raise_for_status()
        return self._decode(resp.text)

    def get_brands(self):
        return self._get('brands.php')

    def get_models(self, brand_id):
        return self._post('models.php', id=brand_id)

    def get_submodels(self, model_id):
        return self._post('submodels.php', id=model_id)

    def list_cars(self, submodel_id):
        return self._post('listcars.php', id=submodel_id)

    def show_car(self, car_id):
        return self._post('showcar.php', id=car_id)


# ---------------------------------------------------------------------------
# Response parsing helpers
# ---------------------------------------------------------------------------

def _parse_showcar(response: dict) -> dict:
    """Convert the numbered showcar response to a flat {label: value} dict."""
    out = {}
    for i in range(len(response) - 1):
        row = response.get(str(i))
        if row and 'p' in row:
            out[row['p']] = row.get('v', '')
    return out


def _iter_cars(response: dict):
    """Yield individual car entries from a numbered listcars response."""
    for i in range(len(response) - 1):
        car = response.get(str(i))
        if car and car.get('v1'):
            yield car


# ---------------------------------------------------------------------------
# Value cleaners
# ---------------------------------------------------------------------------

def _digits(value) -> str | None:
    if not value:
        return None
    return re.sub(r'[^\d]', '', str(value)) or None


def _decimal_str(value) -> str | None:
    if not value:
        return None
    cleaned = re.sub(r'[^\d.]', '', str(value))
    # Collapse repeated dots left by stripping non-decimal chars
    cleaned = re.sub(r'\.{2,}', '.', cleaned).strip('.')
    return cleaned or None


def _int(value) -> int | None:
    try:
        d = _digits(value)
        return int(d) if d else None
    except (ValueError, TypeError):
        return None


def _float(value) -> float | None:
    try:
        d = _decimal_str(value)
        return float(d) if d else None
    except (ValueError, TypeError):
        return None


def _before(raw: str, *delimiters) -> str:
    """Return the substring before the first occurrence of any delimiter."""
    for delim in delimiters:
        if delim in raw:
            raw = raw.split(delim, 1)[0]
    return raw.strip()


# ---------------------------------------------------------------------------
# Field mappings
# ---------------------------------------------------------------------------

def _normalize(value: str) -> str:
    """
    Convert an API label into a compact, underscore-separated identifier.
    Parenthetical clarifications are stripped first so they don't pollute the key.

    Examples:
      "Petrol (Gasoline)"                     → "petrol"
      "Petrol / LPG"                          → "petrol_lpg"
      "Hybrid - petrol / electricity"         → "hybrid_petrol_electricity"
      "SUV"                                   → "suv"
      "Off-road vehicle"                      → "off_road_vehicle"
      "Coupe - Cabriolet"                     → "coupe_cabriolet"
    """
    s = re.sub(r'\(.*?\)', '', value)   # drop parentheticals
    s = s.lower()
    s = re.sub(r'[/\\\-]', ' ', s)     # separators → spaces
    s = re.sub(r'\s+', '_', s.strip()) # whitespace runs → single underscore
    s = re.sub(r'_+', '_', s)          # collapse doubled underscores
    return s


DRIVE_MAP = {
    'Front wheel drive': 'fwd',
    'Rear wheel drive': 'rwd',
    'All wheel drive (4x4)': 'awd',
}

_YEAR_RE = re.compile(r'\b(\d{4})\b')


def _parse_generation_years(name: str):
    """Extract (start_year, end_year) from a generation string like 'E90 (2005-2011)'."""
    years = _YEAR_RE.findall(name)
    start = int(years[0]) if len(years) >= 1 else None
    end = int(years[1]) if len(years) >= 2 else None
    return start, end


# ---------------------------------------------------------------------------
# Spec parser — maps raw API labels to Variant field values
# ---------------------------------------------------------------------------

def _parse_specs(d: dict) -> dict:
    specs = {}

    # Body / layout
    body_raw = d.get('Body type') or d.get('Coupe type')
    if body_raw:
        specs['body_type'] = _normalize(body_raw)

    if d.get('Doors'):
        specs['doors'] = _int(_before(d['Doors'], '/', '-'))

    if d.get('Seats'):
        seats = d['Seats']
        if '/' in seats:
            seats = seats.split('/', 1)[1]
        if '+' in seats:
            parts = seats.split('+')
            seats = str(sum(int(p.strip()) for p in parts if p.strip().isdigit()))
        if '-' in seats:
            seats = seats.split('-', 1)[1]
        specs['seats'] = _int(seats)

    # Engine
    if d.get('Fuel Type'):
        specs['fuel_type'] = _normalize(d['Fuel Type'])

    if d.get('Number of cylinders'):
        specs['engine_cylinders'] = _int(d['Number of cylinders'])

    if d.get('Power'):
        specs['power_hp'] = _int(_before(d['Power'], '/', '@'))

    if d.get('Torque'):
        specs['torque_nm'] = _int(_before(d['Torque'], '/', '@'))

    if d.get('Drive wheel'):
        specs['drive'] = DRIVE_MAP.get(d['Drive wheel'], d['Drive wheel'])

    # Transmission — manual wins if both present; gearbox field is a tiebreaker
    if d.get('Number of Gears (manual transmission)'):
        raw = d['Number of Gears (manual transmission)'].split('/')[0].split()[0]
        specs['number_of_gears'] = _int(raw)
        specs['transmission'] = 'manual'

    if d.get('Number of Gears (automatic transmission)'):
        raw = d['Number of Gears (automatic transmission)'].split('/')[0].split()[0]
        specs['number_of_gears'] = _int(raw)
        specs['transmission'] = 'automatic'

    if d.get('Number of gears and type of gearbox'):
        parts = d['Number of gears and type of gearbox'].split(',', 1)
        specs['number_of_gears'] = _int(parts[0])
        if len(parts) == 2:
            specs['transmission'] = 'manual' if 'manual' in parts[1].lower() else 'automatic'

    # Performance
    if d.get('Maximum speed'):
        specs['top_speed_kmh'] = _int(d['Maximum speed'])

    if d.get('Acceleration 0 - 100 km/h'):
        specs['acceleration_0_100'] = _float(_before(d['Acceleration 0 - 100 km/h'], '-', '/'))

    # Fuel economy (values already in L/100km)
    for api_label, field in [
        ('Fuel consumption (economy) - combined', 'fuel_consumption_l100km'),
        ('Fuel consumption (economy) - urban', 'fuel_consumption_urban_l100km'),
        ('Fuel consumption (economy) - extra urban', 'fuel_consumption_extra_urban_l100km'),
    ]:
        if d.get(api_label):
            specs[field] = _float(_before(d[api_label], '/', '-'))

    tank_raw = d.get('Fuel tank volume') or d.get('Fuel tank capacity')
    if tank_raw:
        specs['fuel_tank_l'] = _int(_before(tank_raw, '/'))

    if d.get('CO2 emissions'):
        specs['co2_g_km'] = _int(d['CO2 emissions'])

    # Electric
    if d.get('All-electric range'):
        specs['all_electric_range'] = _int(d['All-electric range'])

    if d.get('Average Energy consumption'):
        specs['average_energy_consumption'] = _float(_before(d['Average Energy consumption'], '/', '-'))

    # Dimensions & weight
    for api_label, field in [
        ('Length', 'length_mm'),
        ('Width', 'width_mm'),
        ('Height', 'height_mm'),
        ('Wheelbase', 'wheelbase_mm'),
    ]:
        if d.get(api_label):
            specs[field] = _int(_before(d[api_label], '/'))

    if d.get('Kerb Weight'):
        specs['curb_weight_kg'] = _int(_before(d['Kerb Weight'], '/', '-'))

    if d.get('Max. weight'):
        specs['max_weight_kg'] = _int(_before(d['Max. weight'], '/', '-'))

    if d.get('Max load'):
        specs['max_load_kg'] = _int(d['Max load'])

    if d.get('Trunk (boot) space - minimum'):
        specs['trunk_volume_l'] = _int(d['Trunk (boot) space - minimum'])

    return specs


# ---------------------------------------------------------------------------
# Management command
# ---------------------------------------------------------------------------

class Command(BaseCommand):
    help = 'Import car specifications from auto-data.net into the catalog.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--make',
            type=str,
            help='Import only brands whose name contains this string (case-insensitive).',
        )
        parser.add_argument(
            '--delay',
            type=float,
            default=0.1,
            help='Seconds to wait between API requests (default: 1.0).',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Fetch and parse data without writing to the database.',
        )

    def handle(self, *args, **options):
        delay = options['delay']
        make_filter = options.get('make')
        dry_run = options['dry_run']

        api = AutoDataClient()

        self.stdout.write('Fetching brands from auto-data.net…')
        brands = api.get_brands()
        self.stdout.write(f'  Found {len(brands)} brands.')

        if make_filter:
            brands = [b for b in brands if make_filter.lower() in b['na'].lower()]
            self.stdout.write(f'  Filtered to {len(brands)} brand(s) matching "{make_filter}".')

        for brand in brands:
            make_obj = self._upsert_make(brand, dry_run)
            time.sleep(delay)

            try:
                api_models = api.get_models(brand['id'])
            except Exception as exc:
                logger.warning('Failed to fetch models for %s: %s', brand['na'], exc)
                continue

            for api_model in api_models:
                car_model_obj = self._upsert_car_model(api_model, make_obj, dry_run)
                time.sleep(delay)
                try:
                    submodels = api.get_submodels(api_model['id'])
                except Exception as exc:
                    logger.warning('Failed to fetch submodels for %s: %s', api_model.get('na'), exc)
                    continue

                for submodel in submodels:
                    generation_obj = self._upsert_generation(submodel, car_model_obj, dry_run)
                    time.sleep(delay)

                    try:
                        cars_response = api.list_cars(submodel['id'])
                    except Exception as exc:
                        logger.warning('Failed to fetch cars for submodel %s: %s', submodel.get('id'), exc)
                        continue

                    for car in _iter_cars(cars_response):
                        time.sleep(delay)
                        try:
                            spec_response = api.show_car(car['id'])
                        except Exception as exc:
                            logger.warning('Failed to fetch specs for car %s: %s', car.get('id'), exc)
                            continue

                        raw = _parse_showcar(spec_response)
                        self._upsert_variant(car, raw, generation_obj, dry_run)

        self.stdout.write(self.style.SUCCESS('Import complete.'))

    # -----------------------------------------------------------------------
    # Upsert helpers (keyed on data_id — fully idempotent)
    # -----------------------------------------------------------------------

    def _upsert_make(self, brand, dry_run):
        name = brand.get('na', '').strip()
        data_id = brand.get('id')

        if dry_run:
            self.stdout.write(f'[DRY] Make: {name}')
            return None

        obj, created = Make.objects.update_or_create(
            data_id=data_id,
            defaults={'name': name},
        )
        if created:
            self.stdout.write(f'  Created make: {obj.name}')
        return obj

    def _upsert_car_model(self, api_model, make_obj, dry_run):
        """
        api_model: {id, na}  e.g. {"id": 138, "na": "3 Series"}
        """
        model_name = api_model.get('na', '').strip()

        if dry_run:
            self.stdout.write(f'  [DRY] Model: {model_name}')
            return None

        if make_obj is None:
            return None

        obj, created = CarModel.objects.update_or_create(
            make=make_obj,
            name=model_name,
            defaults={'data_id': api_model.get('id')},
        )
        if created:
            self.stdout.write(f'    Created model: {obj}')
        return obj

    def _upsert_generation(self, submodel, car_model_obj, dry_run):
        """
        submodel:     {id, na}  e.g. {"id": 571, "na": "E90 (2005-2011)"}
        car_model_obj: CarModel instance
        """
        name = submodel.get('na', '').strip() or None
        data_id = submodel.get('id')
        production_start, production_end = _parse_generation_years(name or '')

        if dry_run:
            self.stdout.write(f'    [DRY] Generation: {name}')
            return None

        if car_model_obj is None:
            return None

        obj, created = Generation.objects.update_or_create(
            data_id=data_id,
            defaults={
                'car_model': car_model_obj,
                'name': name,
                'production_start': production_start,
                'production_end': production_end,
            },
        )
        if created:
            self.stdout.write(f'      Created generation: {obj}')
        return obj

    def _upsert_variant(self, car, raw_specs, generation_obj, dry_run):
        """
        car:            {v1: "318i 2.0", id: "45360"}  (from listcars)
        raw_specs:      flat {label: value} dict        (from showcar via _parse_showcar)
        generation_obj: Generation instance
        """
        name = car.get('v1', '').strip() or None
        data_id = car.get('id')

        if dry_run:
            self.stdout.write(f'      [DRY] Variant: {name} (id={data_id})')
            return None

        if generation_obj is None:
            return None

        parsed = _parse_specs(raw_specs)
        Variant.objects.update_or_create(
            data_id=data_id,
            defaults={
                'generation': generation_obj,
                'variant': name,
                'scraped_at': timezone.now(),
                **parsed,
            },
        )
