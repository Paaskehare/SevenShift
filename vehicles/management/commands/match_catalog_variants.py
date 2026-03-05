"""
Management command: match_catalog_variants

Attempts to link each Vehicle to a catalog.Variant by scoring candidates on:
  1. Make name  — case-insensitive DB lookup (exact → substring fallback)
  2. Model name — case-insensitive DB lookup (exact → substring fallback)
  3. Transmission — strict hard filter: automatic/manual must agree when both sides
     have a value; mismatches are dropped entirely before scoring
  4. Vehicle year within the generation's production range  (+20 pts)
  5. Fuel type after mobile.de German → catalog slug normalization (+30 pts)
  6. Body type after mobile.de German → catalog slug normalization (+20 pts)
  7. Power output: exact match (+25 pts), within ±10% (+10 pts)
  8. Battery capacity (electric/hybrid): within ±1 kWh (+35 pts), within ±5% (+15 pts)

Only assigns a variant when there is a single candidate at or above MIN_SCORE.
Ties and low-confidence results are flagged but left unassigned.

Usage
─────
  python manage.py match_catalog_variants           # preview (no DB writes)
  python manage.py match_catalog_variants --apply   # write matches
  python manage.py match_catalog_variants --reset   # clear existing, then match
  python manage.py match_catalog_variants --make Audi
  python manage.py match_catalog_variants --verbose
"""

import re

from django.core.management.base import BaseCommand

from catalog.models import Make as CatalogMake, Variant
from vehicles.models import Vehicle


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MIN_SCORE = 30  # minimum to auto-assign; year-alone (20) is not sufficient

# Vehicle.FUEL_CHOICES key (lowercased) → catalog fuel slug fragment.
# The catalog stores slugs like "petrol", "diesel", "hybrid_petrol_electricity".
# We check `catalog_slug.contains(mapped_fragment)` so "petrol" matches all
# petrol variants including hybrids.  Use more specific keys where needed.
FUEL_MAP: dict[str, str] = {
    'petrol':        'petrol',
    'diesel':        'diesel',
    'electricity':   'electric',
    'hybrid_petrol': 'petrol',
    'hybrid_diesel': 'diesel',
    'natural_gas':   'natural_gas',
    'lpg':           'lpg',
}

SCORE_YEAR_IN_RANGE = 20
SCORE_FUEL_MATCH = 30
SCORE_POWER_EXACT = 25
SCORE_POWER_CLOSE = 10    # within ±10%
SCORE_BODY_MATCH = 20
SCORE_BATTERY_EXACT = 35  # within ±1 kWh
SCORE_BATTERY_CLOSE = 15  # within ±5%
SCORE_DOORS_EXACT = 5
SCORE_DOORS_CLOSE = 2     # off by 1 (e.g. hatchback counted with/without tailgate)

# mobile.de German category name (lowercased) → set of matching catalog body_type slugs.
# The catalog slugs come from _normalize() in scrape_catalog, so they are
# lowercase + underscores.  SAV/SAC are BMW marketing terms that appear in the
# catalog but never on mobile.de listings, so they are included as aliases for
# the broader SUV/coupé categories.
BODY_TYPE_MAP: dict[str, set[str]] = {
    'limousine':                    {'sedan'},
    'kombi':                        {'station_wagon', 'station_wagon_,_crossover'},
    'coupé':                        {'coupe', 'coupe,_suv', 'fastback', 'liftback', 'grand_tourer', 'sac'},
    'coupe':                        {'coupe', 'coupe,_suv', 'fastback', 'liftback', 'grand_tourer', 'sac'},
    'suv / geländewagen / pickup':  {'suv', 'sav', 'crossover'},
    'suv / geländewagen':           {'suv', 'sav', 'crossover'},
    'suv':                          {'suv', 'sav', 'crossover'},
    'geländewagen / pickup':        {'suv', 'sav'},
    'cabrio / roadster':            {'cabriolet', 'roadster'},
    'cabrio':                       {'cabriolet'},
    'roadster':                     {'roadster'},
    'kleinwagen':                   {'hatchback', 'liftback'},
    'van / minibus':                {'mpv', 'minivan'},
    'minivan':                      {'minivan', 'mpv'},
    'crossover':                    {'crossover', 'station_wagon_,_crossover'},
}

# Trim keyword fragments (lowercase, checked via `in`) that override the
# mobile.de body-type mapping.  Checked in order — first match wins.
TRIM_BODY_OVERRIDES: list[tuple[str, set[str]]] = [
    ('shooting brake',  {'station_wagon', 'coupe'}),
    ('sportback',       {'liftback', 'fastback'}),
    ('fastback',        {'fastback', 'liftback'}),
    ('liftback',        {'liftback', 'fastback'}),
    ('avant',           {'station_wagon', 'station_wagon_,_crossover'}),
    ('touring',         {'station_wagon', 'station_wagon_,_crossover'}),
    ('allroad',         {'crossover', 'station_wagon_,_crossover'}),
    ('estate',          {'station_wagon', 'station_wagon_,_crossover'}),
    ('targa',           {'cabriolet'}),
]


def _transmission_matches(vehicle: 'Vehicle', variant: 'Variant') -> bool:
    """
    Return False only when both sides have a transmission value and they disagree.
    If either side is blank/null the filter is a no-op (data absent → don't exclude).
    """
    veh = (vehicle.transmission or '').strip()
    cat = (variant.transmission or '').strip()
    if veh and cat:
        return veh == cat
    return True


def _drivetrain_matches(vehicle: 'Vehicle', variant: 'Variant') -> bool:
    """
    Return False only when both sides have a drivetrain value and they disagree.
    If either side is blank/null the filter is a no-op (data absent → don't exclude).
    """
    veh = (vehicle.drivetrain or '').strip()
    cat = (variant.drivetrain or '').strip()
    if veh and cat:
        return veh == cat
    return True


# ---------------------------------------------------------------------------
# DB-driven make / model resolution
# ---------------------------------------------------------------------------

def _find_catalog_make(vehicle_make_name: str) -> 'CatalogMake | None':
    """
    Resolve a vehicle Make name to a catalog Make using database lookups:
    1. Case-insensitive exact match.
    2. Catalog name contains the vehicle name (e.g. "Rolls-Royce" contains "Rolls").
    3. Vehicle name contains the catalog name (e.g. "Mercedes-Benz" contains "Mercedes").
    """
    if not vehicle_make_name:
        return None

    obj = CatalogMake.objects.filter(name__iexact=vehicle_make_name).first()
    if obj:
        return obj

    obj = CatalogMake.objects.filter(name__icontains=vehicle_make_name).first()
    if obj:
        return obj

    lower = vehicle_make_name.lower()
    for catalog_make in CatalogMake.objects.all():
        if catalog_make.name.lower() in lower:
            return catalog_make

    return None


def _find_catalog_models(catalog_make: 'CatalogMake', vehicle_model_name: str) -> list:
    """
    Resolve a vehicle CarModel name to catalog CarModel objects using DB lookups:
    1. Case-insensitive exact match.
    2. Catalog model name contains the vehicle model name.
    3. Vehicle model name contains the catalog model name.
    Returns a deduplicated list ordered by match quality.
    """
    if not vehicle_model_name:
        return []

    seen: set[int] = set()
    results: list = []

    def _add(qs):
        for obj in qs:
            if obj.pk not in seen:
                seen.add(obj.pk)
                results.append(obj)

    _add(catalog_make.models.filter(name__iexact=vehicle_model_name))
    _add(catalog_make.models.filter(name__icontains=vehicle_model_name))

    lower = vehicle_model_name.lower()
    for obj in catalog_make.models.all():
        if obj.pk not in seen and obj.name.lower() in lower:
            seen.add(obj.pk)
            results.append(obj)

    return results


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def _strip_parens(text: str) -> str:
    return re.sub(r'\([^)]*\)', '', text).strip()


def _word_overlap(a: str, b: str) -> int:
    return len(set(re.findall(r'\w+', a.lower())) & set(re.findall(r'\w+', b.lower())))


def _substring_token_score(trim: str, variant_str: str) -> int:
    """
    Score how many characters of variant tokens appear as substrings anywhere
    in the trim string.  This handles concatenated tokens like 'xDrive20d':
    the variant token 'xdrive' is found inside 'xdrive20d' → scores 6,
    while 'sdrive' is not found at all → scores 0.
    """
    trim_lower = trim.lower()
    return sum(
        len(word)
        for word in re.findall(r'\w+', variant_str.lower())
        if word in trim_lower
    )


def _catalog_fuel_key(vehicle_fuel: str) -> str | None:
    return FUEL_MAP.get((vehicle_fuel or '').lower().strip())


def _catalog_body_slugs(mobile_body: str, trim: str = '') -> set[str]:
    """
    Return the set of catalog body_type slugs for a vehicle.
    Trim keywords (e.g. 'sportback', 'avant') take precedence over the
    mobile.de body-type string because mobile.de often misclassifies them
    (e.g. Sportback → 'Limousine' instead of liftback).
    """
    trim_lower = (trim or '').lower()
    for keyword, slugs in TRIM_BODY_OVERRIDES:
        if keyword in trim_lower:
            return slugs
    return BODY_TYPE_MAP.get((mobile_body or '').lower().strip(), set())


def _normalized_body_type(mobile_body: str) -> str:
    """
    Return the single best catalog slug for a mobile.de body type string,
    or '' if unmapped.  When the mapping yields multiple candidates the first
    (alphabetically sorted for determinism) is returned; callers that need the
    full set should use _catalog_body_slugs() instead.
    """
    slugs = _catalog_body_slugs(mobile_body)
    return sorted(slugs)[0] if len(slugs) == 1 else ''


def _score_variant(vehicle: Vehicle, variant: Variant, catalog_fuel_key: str | None, catalog_body_slugs: set[str]) -> int:
    score = 0

    gen = variant.generation
    if vehicle.year:
        start = gen.production_start
        end = gen.production_end
        if start and end and start <= vehicle.year <= end:
            score += SCORE_YEAR_IN_RANGE
        elif start and not end and vehicle.year >= start:
            score += SCORE_YEAR_IN_RANGE
        elif end and not start and vehicle.year <= end:
            score += SCORE_YEAR_IN_RANGE

    if catalog_fuel_key and variant.fuel_type and catalog_fuel_key in variant.fuel_type:
        score += SCORE_FUEL_MATCH

    if catalog_body_slugs and variant.body_type and variant.body_type in catalog_body_slugs:
        score += SCORE_BODY_MATCH

    if vehicle.power_hp and variant.power_hp:
        diff = abs(vehicle.power_hp - variant.power_hp)
        if diff == 0:
            score += SCORE_POWER_EXACT
        elif diff / max(vehicle.power_hp, variant.power_hp) <= 0.10:
            score += SCORE_POWER_CLOSE

    if vehicle.battery_capacity_kwh and variant.gross_battery_capacity:
        veh_kwh = float(vehicle.battery_capacity_kwh)
        cat_kwh = float(variant.gross_battery_capacity)
        diff = abs(veh_kwh - cat_kwh)
        if diff <= 1.0:
            score += SCORE_BATTERY_EXACT
        elif diff / max(veh_kwh, cat_kwh) <= 0.05:
            score += SCORE_BATTERY_CLOSE

    if vehicle.num_doors and variant.doors:
        # this matches only in one direction, either the exact amount, or an additional door
        diff = variant.doors - vehicle.num_doors
        if diff == 0:
            score += SCORE_DOORS_EXACT
        elif diff == 1:
            score += SCORE_DOORS_CLOSE

    return score


def _best_match(vehicle: Vehicle) -> tuple['Variant | None', int, str, list[tuple[int, 'Variant']]]:
    """
    Returns (best_variant, score, reason, top_candidates).
    best_variant is None when no confident unique match was found.
    top_candidates is the sorted [(score, variant), …] list (up to 5 entries).
    """
    if not vehicle.make:
        return None, 0, 'no make set', []

    catalog_make = _find_catalog_make(vehicle.make.name)
    if not catalog_make:
        return None, 0, f'no catalog make for "{vehicle.make.name}"', []

    if not vehicle.model:
        return None, 0, 'no car model set', []

    catalog_models = _find_catalog_models(catalog_make, vehicle.model.name)
    if not catalog_models:
        # Fallback: find Variants whose name starts with the vehicle model name.
        seen: set[int] = set()
        for v in Variant.objects.filter(
            generation__car_model__make=catalog_make,
            variant__istartswith=vehicle.model.name,
        ).select_related('generation__car_model'):
            car_model = v.generation.car_model
            if car_model.pk not in seen:
                seen.add(car_model.pk)
                catalog_models.append(car_model)
    if not catalog_models:
        return None, 0, (
            f'no catalog model for "{vehicle.model.name}" '
            f'under "{catalog_make.name}"'
        ), []

    fuel_key = _catalog_fuel_key(vehicle.fuel_type)
    body_slugs = _catalog_body_slugs(vehicle.mobile_body_type, vehicle.trim)

    scored: list[tuple[int, Variant]] = []
    for catalog_model in catalog_models:
        for v in (
            Variant.objects
            .filter(generation__car_model=catalog_model)
            .select_related('generation')
        ):
            if not _transmission_matches(vehicle, v):
                continue
            if not _drivetrain_matches(vehicle, v):
                continue
            s = _score_variant(vehicle, v, fuel_key, body_slugs)
            scored.append((s, v))

    if not scored:
        return None, 0, 'no variants in catalog for matched model(s)', []

    scored.sort(key=lambda t: t[0], reverse=True)
    best_score, best_variant = scored[0]
    top = scored[:10]
    #top = [(s, v) for s, v in scored if s == best_score]

    if best_score < MIN_SCORE:
        return None, best_score, f'best score {best_score} < threshold {MIN_SCORE}', top

    tied = [v for s, v in scored if s == best_score]
    if len(tied) > 1:
        trim = vehicle.trim or ''
        overlaps = [(v, _word_overlap(trim, _strip_parens(str(v)))) for v in tied]
        best_overlap = max(o for _, o in overlaps)
        winners = [v for v, o in overlaps if o == best_overlap]
        if len(winners) == 1:
            return winners[0], best_score, 'ok (title tiebreak)', top
        # Equal word overlap — fall back to substring token score against trim string.
        fuzzy = [(v, _substring_token_score(trim, _strip_parens(str(v)))) for v in winners]
        best_ratio = max(r for _, r in fuzzy)
        fuzzy_winners = [v for v, r in fuzzy if r == best_ratio]
        if len(fuzzy_winners) == 1:
            return fuzzy_winners[0], best_score, 'ok (fuzzy tiebreak)', top
        return None, best_score, f'ambiguous — {len(tied)} variants share top score {best_score}', top

    return best_variant, best_score, 'ok', top


# ---------------------------------------------------------------------------
# Management command
# ---------------------------------------------------------------------------

class Command(BaseCommand):
    help = (
        'Match vehicles to catalog variants by make, model, year, fuel type, '
        'and power output.  Previews results unless --apply is given.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply',
            action='store_true',
            help='Write matches to the database (default is preview only).',
        )
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Clear existing variant links before matching.',
        )
        parser.add_argument(
            '--make',
            type=str,
            metavar='NAME',
            help='Restrict to vehicles whose make name contains this string.',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Print a line for every vehicle, not just misses and ambiguous cases.',
        )

    def handle(self, *args, **options):
        apply = options['apply']
        reset = options['reset']
        make_filter = options.get('make', '')
        verbose = options['verbose']

        qs = Vehicle.objects.select_related('make', 'model', 'variant')
        if make_filter:
            qs = qs.filter(make__name__icontains=make_filter)
        if not reset:
            qs = qs.filter(variant__isnull=True)

        vehicles = list(qs)
        total = len(vehicles)

        if total == 0:
            self.stdout.write(self.style.WARNING('No vehicles to process.'))
            return

        if reset and apply:
            already_linked = [v for v in vehicles if v.variant_id]
            if already_linked:
                self.stdout.write(f'Clearing {len(already_linked)} existing link(s)…')
                Vehicle.objects.filter(
                    pk__in=[v.pk for v in already_linked]
                ).update(variant=None)
                for v in already_linked:
                    v.variant = None

        self.stdout.write(f'Processing {total} vehicle(s)…\n')

        matched_count = 0
        ambiguous_count = 0
        low_score_count = 0
        no_catalog_count = 0

        for vehicle in vehicles:
            best, score, reason, top = _best_match(vehicle)

            if best is not None:
                matched_count += 1
                if apply:
                    vehicle.variant = best
                    normalized = _normalized_body_type(vehicle.mobile_body_type)
                    update_fields = ['variant']
                    if normalized and not vehicle.body_type:
                        vehicle.body_type = normalized
                        update_fields.append('body_type')
                    vehicle.save(update_fields=update_fields)
                if verbose or apply:
                    self.stdout.write(
                        self.style.SUCCESS(f'  ✓ [{score:3d}] {vehicle}  →  {best}')
                    )
                    trim = re.sub('\s+', ' ', _strip_parens(best.variant))
                    trim += f' - {best.power_hp} hk'
                    self.stdout.write(
                        f'         → {vehicle.make.name} {vehicle.model.name} {trim}'
                    )
            elif reason.startswith('no catalog'):
                no_catalog_count += 1
                if verbose:
                    self.stdout.write(
                        self.style.WARNING(f'  ? [---] {vehicle}  — {reason}')
                    )
            elif 'ambiguous' in reason:
                ambiguous_count += 1
                self.stdout.write(
                    self.style.WARNING(f'  ~ [{score:3d}] {vehicle}  — {reason}')
                )
                for s, v in top:
                    self.stdout.write(f'         [{s:3d}] {v}')
            else:
                low_score_count += 1
                if verbose:
                    self.stdout.write(f'  ✗ [{score:3d}] {vehicle}  — {reason}')
                    for s, v in top:
                        self.stdout.write(f'         [{s:3d}] {v}')

        self.stdout.write('')
        self.stdout.write(f'  Total            : {total}')
        self.stdout.write(self.style.SUCCESS(f'  Matched          : {matched_count}'))
        if ambiguous_count:
            self.stdout.write(self.style.WARNING(f'  Ambiguous        : {ambiguous_count}'))
        if no_catalog_count:
            self.stdout.write(self.style.WARNING(f'  No catalog entry : {no_catalog_count}'))
        if low_score_count:
            self.stdout.write(f'  Low score / miss : {low_score_count}')

        if not apply:
            self.stdout.write(
                self.style.WARNING('\n  Preview only — re-run with --apply to save.')
            )
        else:
            self.stdout.write(self.style.SUCCESS('\n  Done.'))
