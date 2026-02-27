"""
Management command: scrape_mobile_de

Searches mobile.de using stored MobileDeSearchConfig records and saves
results as Vehicle objects.

Usage
─────
  python manage.py scrape_mobile_de                  # run all active configs
  python manage.py scrape_mobile_de --config "BMW 3er"
  python manage.py scrape_mobile_de --dry-run
  python manage.py scrape_mobile_de --delay 3.0 --no-details

How mobile.de IDs work
──────────────────────
Each Make / CarModel row in the vehicles app can store a mobile_de_id.
Set these via the admin, then link the Make/CarModel to a MobileDeSearchConfig.
The scraper builds the ms= URL parameter as  "MAKE_ID;MODEL_ID;;"  automatically.

To find the IDs: search on suchen.mobile.de, copy the resulting URL, and read
the  ms=  parameter value.  E.g. ms=3500%3B3%3B%3B  →  "3500;3;;"
 → MAKE_ID=3500, MODEL_ID=3.

HTML/JSON structure note
────────────────────────
mobile.de is a Next.js app.  The scraper first looks for a  __NEXT_DATA__
JSON blob in the page.  If the JSON paths change (mobile.de deploys frequently),
update _find_ads_in_json() and _parse_ad_json().  The HTML fallback uses
CSS selectors that may also need updating after a site redesign.

HTTP client note
────────────────
Uses Scrapling's DynamicSession (Playwright/Chromium under the hood) with
network_idle=True so Akamai's challenge JS can complete before the page is
returned.  Set MOBILE_DE_PROXY env var to a proxy URL to route requests
through a proxy (e.g. http://user:pass@host:port).
"""

import json
import logging
import os
import re
import time
from urllib.parse import urlencode, urljoin

from bs4 import BeautifulSoup
from camoufox.sync_api import Camoufox
from django.core.management.base import BaseCommand
from django.utils import timezone

from vehicles.models import (
    Make, CarModel, MobileDeSearchConfig, Vehicle, VehicleImage,
)

logger = logging.getLogger(__name__)

BASE_URL = 'https://suchen.mobile.de'
SEARCH_PATH = '/fahrzeuge/search.html'
DETAIL_PATH = '/fahrzeuge/details.html'

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:145.0) Gecko/20100101 Firefox/145.0',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate, br, zstd',
    'Referer': 'https://www.mobile.de/',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'same-site',
    'Sec-Fetch-User': '?1',
    'DNT': '1',
    'Sec-GPC': '1',
    'Priority': 'u=0, i',
    'TE': 'trailers',
}

# ---------------------------------------------------------------------------
# HTTP client — camoufox (hardened Firefox, handles Akamai natively)
# ---------------------------------------------------------------------------
#
# Mobile.de serves a JS challenge to Firefox which the browser solves, but
# hard-blocks headless Chromium with a straight 403.  Camoufox is a patched
# Firefox build (via Playwright) that defeats most fingerprinting vectors.
# The browser stays open for the whole scrape so Akamai cookies persist.

NAV_TIMEOUT = 60_000   # ms — generous for challenge + page load
SETTLE_MS   = 3_000    # ms — poll interval while waiting for challenge to clear


def _is_akamai_challenge(html: str) -> bool:
    return 'sec-if-cpt-container' in html or 'akamai-logo' in html


class MobileDeClient:
    def __init__(self, delay: float = 2.0):
        self.delay = delay
        proxy_url = os.environ.get('MOBILE_DE_PROXY', '').strip()

        camoufox_kwargs: dict = {'headless': True}
        if proxy_url:
            camoufox_kwargs['proxy'] = {'server': proxy_url}

        self._cm = Camoufox(**camoufox_kwargs)
        self._browser = self._cm.__enter__()
        self._context = self._browser.new_context(locale='en-US')
        self._context.set_extra_http_headers({k: HEADERS[k] for k in (
            'Accept', 'Accept-Language', 'Referer', 'DNT', 'Sec-GPC',
        )})
        self._page = self._context.new_page()
        self._warmup()

    def _warmup(self):
        """Visit the homepage so Akamai issues its initial cookies."""
        logger.info('Browser warmup: visiting mobile.de homepage…')
        self._navigate('https://www.mobile.de/')

    def _navigate(self, url: str) -> str:
        """Navigate to *url*, wait for any Akamai challenge to clear, return HTML."""
        try:
            self._page.goto(url, wait_until='domcontentloaded', timeout=NAV_TIMEOUT)
        except Exception as exc:
            logger.warning('Navigation error for %s: %s', url, exc)

        for attempt in range(15):           # up to 45 s
            self._page.wait_for_timeout(SETTLE_MS)
            html = self._page.content()
            if not _is_akamai_challenge(html):
                if attempt:
                    logger.info('Akamai challenge cleared after ~%d s.', (attempt + 1) * 3)
                return html
            logger.debug('Challenge still active (%d/15)…', attempt + 1)

        logger.warning('Akamai challenge did not clear after 45 s — returning page as-is.')
        return self._page.content()

    def _get(self, url: str, params: dict | None = None) -> str:
        time.sleep(self.delay)
        if params:
            url = f'{url}?{urlencode(params)}'
        return self._navigate(url)

    def search_page(self, params: dict, page: int = 1) -> str:
        p = {**params, 'dam': 'false', 's': 'Car', 'vc': 'Car',
             'pageNumber': page, 'isSearchRequest': 'true'}
        return self._get(BASE_URL + SEARCH_PATH, params=p)

    def detail_page(self, listing_id: str) -> str:
        return self._get(BASE_URL + DETAIL_PATH, params={'id': listing_id})

    def close(self):
        try:
            self._cm.__exit__(None, None, None)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Search URL builder
# ---------------------------------------------------------------------------

def build_search_params(config: MobileDeSearchConfig) -> dict:
    """Convert a MobileDeSearchConfig into mobile.de query parameters."""
    params = {}

    # Build ms= from make/model mobile_de_id when available
    make_id = config.make.mobile_de_id if config.make else None
    model_id = config.car_model.mobile_de_id if config.car_model else None
    if make_id:
        ms = f'{make_id};{model_id if model_id else ""};;'
        params['ms'] = ms

    if config.year_from:
        params['minFirstRegistrationDate'] = f'{config.year_from}-01-01'
    if config.year_to:
        params['maxFirstRegistrationDate'] = f'{config.year_to}-12-31'
    if config.price_min:
        params['minPrice'] = config.price_min
    if config.price_max:
        params['maxPrice'] = config.price_max
    if config.mileage_max:
        params['maxMileage'] = config.mileage_max
    if config.fuel_type:
        params['fuelType.values'] = config.fuel_type

    return params


# ---------------------------------------------------------------------------
# JSON extraction (Next.js __NEXT_DATA__)
# ---------------------------------------------------------------------------

def _extract_next_data(html: str) -> dict | None:
    """Return the parsed __NEXT_DATA__ JSON object, or None if not found."""
    soup = BeautifulSoup(html, 'html.parser')
    tag = soup.find('script', {'id': '__NEXT_DATA__'})
    if tag and tag.string:
        try:
            return json.loads(tag.string)
        except json.JSONDecodeError:
            pass
    return None


def _find_ads_in_json(data: dict) -> list[dict]:
    """
    Navigate the Next.js props structure to find the list of ad objects.

    mobile.de path (as observed): props → pageProps → searchResult → ads
    If mobile.de restructures their JSON, update this function.
    """
    try:
        return data['props']['pageProps']['searchResult']['ads']
    except (KeyError, TypeError):
        pass
    # Fallback: try a different common path
    try:
        return data['props']['pageProps']['listings']
    except (KeyError, TypeError):
        pass
    return []


def _total_count_from_json(data: dict) -> int | None:
    try:
        return data['props']['pageProps']['searchResult']['numTotalAds']
    except (KeyError, TypeError):
        return None


def _parse_ad_json(ad: dict) -> dict | None:
    """
    Extract a normalised listing dict from a single ad object in the JSON.

    Field names are based on the mobile.de Next.js API as observed.
    Update keys here if mobile.de changes their API response shape.
    """
    listing_id = str(ad.get('id', '')).strip()
    if not listing_id:
        return None

    out = {'listing_id': listing_id}

    # URL
    url_path = ad.get('url') or ad.get('relativeUrl') or ''
    out['source_url'] = urljoin(BASE_URL, url_path) if url_path else ''

    # Make / model / trim — may be nested or flat depending on API version
    out['make_name'] = (
        (ad.get('make') or {}).get('name')
        or ad.get('make')
        or ''
    )
    out['model_name'] = (
        (ad.get('model') or {}).get('name')
        or ad.get('model')
        or ''
    )
    out['trim'] = ad.get('version') or ad.get('trim') or ad.get('title', '')

    # Year / first registration
    reg = ad.get('firstRegistrationDate') or ad.get('firstRegistration') or ''
    out['first_registration'] = str(reg)[:7]   # keep MM/YYYY or YYYY-MM
    out['year'] = _year_from_reg(out['first_registration'])

    # Price
    price_obj = ad.get('price') or {}
    out['price'] = _to_decimal(
        price_obj.get('amount') or price_obj.get('rawPrice') or ad.get('price')
    )
    out['price_vat'] = bool(price_obj.get('vatDeductible'))
    out['price_vat_applicable'] = not bool(ad.get('privateOffer'))

    # Condition
    out['mileage_km'] = _to_int(ad.get('mileageInKm') or ad.get('mileage'))

    # Specs
    fuel_obj = ad.get('fuelType') or {}
    out['fuel_type'] = (
        fuel_obj.get('value') if isinstance(fuel_obj, dict) else str(fuel_obj)
    )
    perf = ad.get('power') or ad.get('performance') or {}
    out['power_hp'] = _to_int(
        perf.get('ps') or perf.get('hp') if isinstance(perf, dict) else perf
    )
    out['battery_capacity_kwh'] = _to_decimal(
        (ad.get('battery') or {}).get('capacityInKwh')
    )
    out['body_type'] = (ad.get('category') or {}).get('name', '') if isinstance(ad.get('category'), dict) else ''

    # Appearance
    color_obj = ad.get('exteriorColor') or {}
    out['color'] = color_obj.get('colorDescription') or color_obj.get('name', '') if isinstance(color_obj, dict) else ''
    interior_obj = ad.get('interiorColor') or {}
    out['interior_color'] = interior_obj.get('colorDescription') or interior_obj.get('name', '') if isinstance(interior_obj, dict) else ''

    # Images
    images = ad.get('images') or ad.get('imageUrls') or []
    out['image_urls'] = [
        img.get('url') or img if isinstance(img, str) else ''
        for img in images
    ]
    out['image_urls'] = [u for u in out['image_urls'] if u]
    out['thumbnail_url'] = out['image_urls'][0] if out['image_urls'] else ''

    # Equipment not available at list level — populated later from detail page
    out['equipment'] = []

    return out


# ---------------------------------------------------------------------------
# HTML fallback parser (search results page)
# ---------------------------------------------------------------------------

def _parse_search_html(html: str) -> list[dict]:
    """
    Extract listing summaries from HTML when JSON is unavailable.
    Tries several common CSS selectors used by mobile.de over time.
    """
    soup = BeautifulSoup(html, 'html.parser')
    cards = (
        soup.select('article[data-listing-id]')
        or soup.select('li[data-ad-id]')
        or soup.select('.cpo-tile')
        or soup.select('[data-testid="result-listing"]')
    )
    listings = []
    for card in cards:
        d = _parse_card_html(card)
        if d:
            listings.append(d)
    return listings


def _parse_card_html(card) -> dict | None:
    listing_id = (
        card.get('data-listing-id')
        or card.get('data-ad-id')
        or card.get('id', '').replace('listing-', '')
    )
    if not listing_id:
        return None

    title = _text(card.select_one(
        'h2, .cpo-tile__headline, [data-testid="listing-title"], .vehicle-title'
    ))
    price_raw = _text(card.select_one(
        '.price-primary, .cpo-tile__price, [data-testid="price-label"], .u-text-emphasis'
    ))
    link = card.select_one('a[href*="fahrzeuge"]')
    url = urljoin(BASE_URL, link['href']) if link else ''

    # Mileage / first-reg / power often appear in a details row
    details_text = _text(card.select_one('.vehicle-details, .cpo-tile__details, .u-text-subdued'))

    return {
        'listing_id': str(listing_id),
        'source_url': url,
        'make_name': '',   # hard to parse from card — populated from detail page
        'model_name': '',
        'trim': title,
        'first_registration': _extract_reg(details_text),
        'year': _year_from_reg(_extract_reg(details_text)),
        'price': _parse_price(price_raw),
        'price_vat': False,
        'price_vat_applicable': True,
        'mileage_km': _extract_mileage(details_text),
        'fuel_type': '',
        'power_hp': _extract_power(details_text),
        'battery_capacity_kwh': None,
        'body_type': '',
        'color': '',
        'interior_color': '',
        'image_urls': [img['src'] for img in card.select('img[src]') if img.get('src')],
        'thumbnail_url': (card.select_one('img[src]') or {}).get('src', ''),
        'equipment': [],
    }


# ---------------------------------------------------------------------------
# Detail page parser
# ---------------------------------------------------------------------------

def _parse_detail_page(html: str, base: dict) -> dict:
    """
    Enrich a listing dict with data from the individual detail page.
    Tries JSON first, then HTML.
    """
    data = _extract_next_data(html)
    if data:
        ad = (
            (data.get('props') or {}).get('pageProps') or {}
        ).get('ad') or (
            (data.get('props') or {}).get('pageProps') or {}
        ).get('vehicle') or {}
        if ad:
            full = _parse_ad_json(ad)
            if full:
                # Merge: full detail takes precedence but keep base listing_id
                full['listing_id'] = base['listing_id']
                full['equipment'] = _extract_equipment_json(ad)
                return full

    # HTML fallback for detail page
    soup = BeautifulSoup(html, 'html.parser')

    # Equipment / features list
    equip_items = soup.select(
        '.cpo-features li, .feature-list li, [data-testid="feature-item"], '
        '.vehicle-features__item'
    )
    base['equipment'] = [_text(el) for el in equip_items if _text(el)]

    # Battery capacity
    for label_el in soup.select('dt, .detail-label, [data-testid*="label"]'):
        label = _text(label_el).lower()
        val_el = label_el.find_next_sibling()
        val = _text(val_el) if val_el else ''
        if 'batterie' in label or 'battery' in label or 'akku' in label:
            base['battery_capacity_kwh'] = _to_decimal(_digits(val))
        if 'innenfarbe' in label or 'interior' in label:
            base['interior_color'] = val
        if 'karosserie' in label or 'body' in label:
            base['body_type'] = val

    return base


def _extract_equipment_json(ad: dict) -> list[str]:
    """Pull equipment strings from an ad JSON object."""
    items = (
        ad.get('features')
        or ad.get('equipment')
        or ad.get('equipmentList')
        or []
    )
    result = []
    for item in items:
        if isinstance(item, str):
            result.append(item)
        elif isinstance(item, dict):
            result.append(item.get('description') or item.get('name') or '')
    return [s for s in result if s]


# ---------------------------------------------------------------------------
# Value helpers
# ---------------------------------------------------------------------------

def _text(el) -> str:
    return el.get_text(strip=True) if el else ''


_YEAR_RE = re.compile(r'\b(19|20)\d{2}\b')
_MILEAGE_RE = re.compile(r'([\d.,]+)\s*km', re.IGNORECASE)
_POWER_RE = re.compile(r'(\d+)\s*(?:PS|hp|kW)', re.IGNORECASE)
_PRICE_RE = re.compile(r'([\d.,]+)')
_REG_RE = re.compile(r'(\d{2}/\d{4}|\d{4}-\d{2})')


def _year_from_reg(reg: str) -> int | None:
    m = _YEAR_RE.search(reg)
    return int(m.group()) if m else None


def _extract_reg(text: str) -> str:
    m = _REG_RE.search(text or '')
    return m.group() if m else ''


def _extract_mileage(text: str) -> int | None:
    m = _MILEAGE_RE.search(text or '')
    if m:
        return _to_int(m.group(1))
    return None


def _extract_power(text: str) -> int | None:
    m = _POWER_RE.search(text or '')
    return int(m.group(1)) if m else None


def _parse_price(raw: str) -> float | None:
    if not raw:
        return None
    m = _PRICE_RE.search(raw.replace('.', '').replace(',', '.'))
    return float(m.group(1)) if m else None


def _digits(value) -> str | None:
    if not value:
        return None
    return re.sub(r'[^\d]', '', str(value)) or None


def _to_int(value) -> int | None:
    try:
        d = _digits(value)
        return int(d) if d else None
    except (ValueError, TypeError):
        return None


def _to_decimal(value):
    if value is None:
        return None
    try:
        cleaned = re.sub(r'[^\d.]', '', str(value))
        return float(cleaned) if cleaned else None
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def _get_or_create_make(name: str) -> Make | None:
    if not name:
        return None
    obj, _ = Make.objects.get_or_create(name=name.strip())
    return obj


def _get_or_create_car_model(model_name: str, make: Make | None) -> CarModel | None:
    if not model_name or not make:
        return None
    obj, _ = CarModel.objects.get_or_create(make=make, name=model_name.strip())
    return obj


def _upsert_vehicle(listing: dict, config: MobileDeSearchConfig, dry_run: bool):
    listing_id = listing['listing_id']
    make_obj = _get_or_create_make(listing.get('make_name', ''))
    model_obj = _get_or_create_car_model(listing.get('model_name', ''), make_obj)

    defaults = {
        'search_config': config,
        'make': make_obj,
        'car_model': model_obj,
        'source_url': listing.get('source_url', ''),
        'trim': listing.get('trim', ''),
        'year': listing.get('year'),
        'first_registration': listing.get('first_registration', ''),
        'body_type': listing.get('body_type', ''),
        'price': listing.get('price'),
        'price_vat': listing.get('price_vat', False),
        'price_vat_applicable': listing.get('price_vat_applicable', True),
        'mileage_km': listing.get('mileage_km'),
        'fuel_type': listing.get('fuel_type', ''),
        'power_hp': listing.get('power_hp'),
        'battery_capacity_kwh': listing.get('battery_capacity_kwh'),
        'color': listing.get('color', ''),
        'interior_color': listing.get('interior_color', ''),
        'equipment': listing.get('equipment', []),
        'thumbnail_url': listing.get('thumbnail_url', ''),
        'is_active': True,
    }

    if dry_run:
        make_str = listing.get('make_name', '?')
        model_str = listing.get('model_name', '?')
        logger.info('[DRY] %s %s %s — %s km @ %s €',
                    make_str, model_str, listing.get('trim', ''),
                    listing.get('mileage_km', '?'), listing.get('price', '?'))
        return

    vehicle, created = Vehicle.objects.update_or_create(
        listing_id=listing_id,
        defaults=defaults,
    )

    # Sync images only on create or when image list changed
    image_urls = listing.get('image_urls', [])
    if image_urls:
        existing = list(vehicle.images.values_list('url', flat=True))
        if set(image_urls) != set(existing):
            vehicle.images.all().delete()
            VehicleImage.objects.bulk_create([
                VehicleImage(vehicle=vehicle, url=url, order=i)
                for i, url in enumerate(image_urls)
            ])

    action = 'Created' if created else 'Updated'
    logger.info('%s vehicle %s: %s', action, listing_id, vehicle)
    return vehicle


# ---------------------------------------------------------------------------
# Management command
# ---------------------------------------------------------------------------

class Command(BaseCommand):
    help = 'Scrape vehicle listings from mobile.de into the Vehicle model.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--config',
            type=str,
            metavar='NAME',
            help='Run only the search config whose name matches this string.',
        )
        parser.add_argument(
            '--delay',
            type=float,
            default=2.0,
            help='Seconds to wait between HTTP requests (default: 2.0).',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Parse and log results without writing to the database.',
        )
        parser.add_argument(
            '--no-details',
            action='store_true',
            help='Skip fetching individual listing detail pages (faster, less data).',
        )
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Dump the raw first-page HTML and __NEXT_DATA__ structure to /tmp/mobile_de_debug.*',
        )

    def handle(self, *args, **options):
        # Playwright's sync API runs an asyncio event loop internally.
        # Django 5 detects any running loop as an "async context" and blocks
        # synchronous ORM calls.  This env var disables that guard — safe here
        # because a management command is single-threaded with no concurrent
        # async ORM access.
        os.environ.setdefault('DJANGO_ALLOW_ASYNC_UNSAFE', 'true')

        delay = options['delay']
        dry_run = options['dry_run']
        fetch_details = not options['no_details']
        config_filter = options.get('config')
        debug = options.get('debug', False)

        configs = MobileDeSearchConfig.objects.filter(is_active=True)
        if config_filter:
            configs = configs.filter(name__icontains=config_filter)

        if not configs.exists():
            self.stdout.write(self.style.WARNING('No active search configs found.'))
            return

        client = MobileDeClient(delay=delay)
        try:
            for config in configs:
                self.stdout.write(f'\n▶ Running config: {config}')
                try:
                    seen_ids = self._run_config(config, client, dry_run, fetch_details, debug=debug)
                except Exception as exc:
                    logger.error('Config "%s" failed: %s', config, exc, exc_info=True)
                    self.stdout.write(self.style.ERROR(f'  Failed: {exc}'))
                    continue

                if not dry_run:
                    # Mark listings that have disappeared from results as inactive
                    deactivated = (
                        Vehicle.objects
                        .filter(search_config=config, is_active=True)
                        .exclude(listing_id__in=seen_ids)
                        .update(is_active=False)
                    )
                    if deactivated:
                        self.stdout.write(f'  Deactivated {deactivated} stale listing(s).')

                    config.last_run_at = timezone.now()
                    config.save(update_fields=['last_run_at'])
        finally:
            client.close()

        self.stdout.write(self.style.SUCCESS('\nScrape complete.'))

    def _run_config(
        self,
        config: MobileDeSearchConfig,
        client: MobileDeClient,
        dry_run: bool,
        fetch_details: bool,
        debug: bool = False,
    ) -> list[str]:
        """Run one config. Returns list of listing_ids seen in search results."""
        params = build_search_params(config)
        seen_ids: list[str] = []
        page = 1
        total_fetched = 0

        while total_fetched < config.max_results:
            self.stdout.write(f'  Fetching page {page}…')
            try:
                html = client.search_page(params, page=page)
            except Exception as exc:
                logger.warning('HTTP error on page %d: %s', page, exc)
                break

            if debug and page == 1:
                self._dump_debug(html, config)

            listings = self._extract_listings(html)
            if not listings:
                self.stdout.write('  No more listings.')
                break

            for listing in listings:
                if total_fetched >= config.max_results:
                    break

                listing_id = listing.get('listing_id', '')
                if not listing_id:
                    continue

                # Optionally enrich with detail page
                if fetch_details:
                    try:
                        detail_html = client.detail_page(listing_id)
                        listing = _parse_detail_page(detail_html, listing)
                    except Exception as exc:
                        logger.warning('Detail page failed for %s: %s', listing_id, exc)

                _upsert_vehicle(listing, config, dry_run)
                seen_ids.append(listing_id)
                total_fetched += 1

            self.stdout.write(f'  Page {page}: {len(listings)} listing(s) found ({total_fetched} total).')
            page += 1

        return seen_ids

    def _dump_debug(self, html: str, config):
        """Write raw HTML and __NEXT_DATA__ structure to /tmp for inspection."""
        import pathlib
        slug = re.sub(r'[^a-z0-9]', '_', str(config).lower())
        html_path = pathlib.Path(f'/tmp/mobile_de_debug_{slug}.html')
        html_path.write_text(html, encoding='utf-8')
        self.stdout.write(self.style.WARNING(f'  [debug] HTML saved → {html_path}'))

        data = _extract_next_data(html)
        if not data:
            self.stdout.write(self.style.ERROR('  [debug] No __NEXT_DATA__ found in page.'))
            return

        json_path = pathlib.Path(f'/tmp/mobile_de_debug_{slug}.json')
        json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
        self.stdout.write(self.style.WARNING(f'  [debug] __NEXT_DATA__ saved → {json_path}'))

        # Print top-level structure so you can trace the path to listings
        def _keys(d, depth=0, max_depth=4):
            if depth >= max_depth or not isinstance(d, dict):
                return
            for k, v in d.items():
                kind = f'[{len(v)}]' if isinstance(v, list) else ''
                self.stdout.write('  ' + '  ' * depth + f'  {k}{kind}')
                _keys(v, depth + 1, max_depth)

        self.stdout.write('  [debug] __NEXT_DATA__ structure:')
        _keys(data)

    def _extract_listings(self, html: str) -> list[dict]:
        """Try JSON extraction first, fall back to HTML parsing."""
        data = _extract_next_data(html)
        if data:
            ads = _find_ads_in_json(data)
            if ads:
                results = []
                for ad in ads:
                    parsed = _parse_ad_json(ad)
                    if parsed:
                        results.append(parsed)
                return results

        # HTML fallback
        return _parse_search_html(html)
