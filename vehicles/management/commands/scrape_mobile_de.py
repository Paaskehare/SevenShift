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

import requests

from bs4 import BeautifulSoup
from decouple import config as env_config
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


def _is_js_challenge(html: str) -> bool:
    """Return True if the page is a solvable Akamai JS challenge (wait it out)."""
    return 'sec-if-cpt-container' in html or 'akamai-logo' in html


def _is_hard_blocked(html: str) -> bool:
    """Return True if the page is a permanent bot block (cannot be solved by waiting)."""
    return (
        'Zugriff verweigert' in html
        or 'Reference Error:' in html
    )


class MobileDeClient:
    def __init__(self, delay: float = 2.0):
        self.delay = delay
        proxy_url = env_config('MOBILE_DE_PROXY', default='').strip()

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
        """Visit both subdomains so Akamai issues cookies for each."""
        logger.info('Browser warmup: visiting mobile.de…')
        self._navigate('https://www.mobile.de/')
        logger.info('Browser warmup: visiting suchen.mobile.de…')
        self._navigate('https://suchen.mobile.de/')

    def _navigate(self, url: str) -> str:
        """Navigate to *url*, wait for any Akamai block/challenge to clear, return HTML."""
        try:
            self._page.goto(url, wait_until='domcontentloaded', timeout=NAV_TIMEOUT)
        except Exception as exc:
            logger.warning('Navigation error for %s: %s', url, exc)

        # Check once before polling — fail fast on hard blocks
        html = self._page.content()
        if _is_hard_blocked(html):
            raise RuntimeError(
                f'Hard bot-block (Access denied) on {url}. '
                'Try setting MOBILE_DE_PROXY env var or run again later.'
            )

        for attempt in range(15):           # up to 45 s for JS challenges
            if not _is_js_challenge(html):
                if attempt:
                    logger.info('JS challenge cleared after ~%d s.', (attempt + 1) * 3)
                return html
            logger.debug('JS challenge active (%d/15)…', attempt + 1)
            self._page.wait_for_timeout(SETTLE_MS)
            html = self._page.content()
            if _is_hard_blocked(html):
                raise RuntimeError(
                    f'Hard bot-block (Access denied) on {url}. '
                    'Try setting MOBILE_DE_PROXY env var or run again later.'
                )

        logger.warning('JS challenge did not clear after 45 s — returning page as-is.')
        return html

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
    """
    Return the page's embedded JSON data, or None if not found.

    Tries in order:
    1. window.__INITIAL_STATE__ (current mobile.de format)
    2. <script id="__NEXT_DATA__"> (legacy Next.js format)
    """
    soup = BeautifulSoup(html, 'html.parser')

    # Current format: window.__INITIAL_STATE__ = {...};
    for tag in soup.find_all('script'):
        text = tag.string or ''
        if 'window.__INITIAL_STATE__' in text:
            m = re.search(r'window\.__INITIAL_STATE__\s*=\s*', text)
            if m:
                try:
                    data, _ = json.JSONDecoder().raw_decode(text, m.end())
                    return data
                except json.JSONDecodeError:
                    pass

    # Legacy format: <script id="__NEXT_DATA__" type="application/json">
    tag = soup.find('script', {'id': '__NEXT_DATA__'})
    if tag and tag.string:
        try:
            return json.loads(tag.string)
        except json.JSONDecodeError:
            pass

    return None


def _find_ads_in_json(data: dict) -> list[dict]:
    """
    Return the list of ad objects from the page JSON.

    Tries the current __INITIAL_STATE__ path first, then legacy __NEXT_DATA__ paths.
    """
    # Current: search → srp → data → searchResults → items
    try:
        return data['search']['srp']['data']['searchResults']['items']
    except (KeyError, TypeError):
        pass
    # Legacy: props → pageProps → searchResult → ads
    try:
        return data['props']['pageProps']['searchResult']['ads']
    except (KeyError, TypeError):
        pass
    try:
        return data['props']['pageProps']['listings']
    except (KeyError, TypeError):
        pass
    return []


def _total_count_from_json(data: dict) -> int | None:
    # Current __INITIAL_STATE__ path
    try:
        return data['search']['srp']['data']['searchResults']['numResultsTotal']
    except (KeyError, TypeError):
        pass
    # Legacy __NEXT_DATA__ path
    try:
        return data['props']['pageProps']['searchResult']['numTotalAds']
    except (KeyError, TypeError):
        return None


def _parse_ad_json(ad: dict) -> dict | None:
    """
    Extract a normalised listing dict from a single ad object in the JSON.

    Handles both the current __INITIAL_STATE__ format and the legacy
    __NEXT_DATA__ format.  Key differences in the current format:
      - make/model are plain strings, not nested dicts
      - attr dict holds fr (registration), ml (mileage), pw (power), ft (fuel), ecol (colour)
      - price.grossAmount is an int; no vatDeductible
      - previewImage + previewThumbnails replace the images array
    """
    listing_id = str(ad.get('id', '')).strip()
    if not listing_id:
        return None

    out = {'listing_id': listing_id}

    # URL
    url_path = ad.get('relativeUrl') or ad.get('url') or ''
    out['source_url'] = urljoin(BASE_URL, url_path) if url_path else ''

    # Make / model — current: flat strings; legacy: nested dicts
    make = ad.get('make') or {}
    out['make_name'] = make.get('name', '') if isinstance(make, dict) else str(make)
    model = ad.get('model') or {}
    out['model_name'] = model.get('name', '') if isinstance(model, dict) else str(model)
    out['trim'] = ad.get('subTitle') or ad.get('version') or ad.get('trim') or ad.get('title', '')

    # Year / first registration
    # Current: attr.fr = "01/2023"; legacy: firstRegistrationDate = "2023-01"
    attr = ad.get('attr') or {}
    reg = attr.get('fr') or ad.get('firstRegistrationDate') or ad.get('firstRegistration') or ''
    out['first_registration'] = str(reg)[:7]
    out['year'] = _year_from_reg(out['first_registration'])

    # Price
    # Current: price.grossAmount (int); legacy: price.amount
    price_obj = ad.get('price') or {}
    if isinstance(price_obj, dict):
        out['price'] = _to_decimal(
            price_obj.get('grossAmount') or price_obj.get('amount') or price_obj.get('rawPrice')
        )
        out['price_vat'] = bool(price_obj.get('vatDeductible'))
    else:
        out['price'] = _to_decimal(price_obj)
        out['price_vat'] = False
    out['price_vat_exempt'] = bool(ad.get('privateOffer'))

    # Mileage — current: attr.ml = "24.000 km"; _to_int strips non-digits safely
    out['mileage_km'] = _to_int(attr.get('ml') or ad.get('mileageInKm') or ad.get('mileage'))

    # Fuel type — current: attr.ft = "Benzin"; legacy: fuelType.value
    fuel_obj = ad.get('fuelType') or {}
    out['fuel_type'] = attr.get('ft') or (
        fuel_obj.get('value') if isinstance(fuel_obj, dict) else str(fuel_obj or '')
    )

    # Power — current: attr.pw = "81 kW (110 PS)"; extract PS value
    pw_raw = attr.get('pw') or ''
    if pw_raw:
        ps_m = re.search(r'(\d+)\s*PS', pw_raw, re.IGNORECASE)
        out['power_hp'] = int(ps_m.group(1)) if ps_m else None
    else:
        perf = ad.get('power') or ad.get('performance') or {}
        out['power_hp'] = _to_int(
            perf.get('ps') or perf.get('hp') if isinstance(perf, dict) else perf
        )

    out['battery_capacity_kwh'] = _to_decimal(
        (ad.get('battery') or {}).get('capacityInKwh')
    )

    # Body type — current: plain string; legacy: dict
    cat = ad.get('category') or {}
    out['body_type'] = cat.get('name', '') if isinstance(cat, dict) else str(cat)

    # Colour — current: attr.ecol; legacy: exteriorColor dict
    color_obj = ad.get('exteriorColor') or {}
    out['color'] = attr.get('ecol') or (
        color_obj.get('colorDescription') or color_obj.get('name', '')
        if isinstance(color_obj, dict) else ''
    )
    interior_obj = ad.get('interiorColor') or {}
    out['interior_color'] = (
        interior_obj.get('colorDescription') or interior_obj.get('name', '')
        if isinstance(interior_obj, dict) else ''
    )

    # Images — current: previewThumbnails (list of dicts with src); legacy: images array
    # Upgrade all image URLs from thumbnail size to full-size (1600w).
    preview = ad.get('previewImage') or {}
    thumb_src = preview.get('src', '') if isinstance(preview, dict) else ''
    raw_images = ad.get('previewThumbnails') or ad.get('images') or ad.get('imageUrls') or []
    image_urls = []
    for img in raw_images:
        if isinstance(img, str):
            image_urls.append(_hd_image_url(img))
        elif isinstance(img, dict):
            src = img.get('src') or img.get('url') or ''
            if src:
                image_urls.append(_hd_image_url(src))
    out['image_urls'] = [u for u in image_urls if u]
    out['thumbnail_url'] = _hd_image_url(thumb_src) if thumb_src else (
        out['image_urls'][0] if out['image_urls'] else ''
    )

    # Price rating
    pr = ad.get('priceRating') or {}
    out['price_rating'] = pr.get('rating', '')
    raw_thresholds = pr.get('thresholdLabels') or []
    out['price_rating_thresholds'] = [
        v for v in (_parse_german_price_str(s) for s in raw_thresholds if isinstance(s, str))
        if v is not None
    ]

    # Seller info — contactInfo.country / contactInfo.sellerType
    contact = ad.get('contactInfo') or {}
    out['country'] = contact.get('country', '') or attr.get('cn', '')
    out['seller_type'] = contact.get('sellerType', '')

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
        'price_vat_exempt': False,
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


def _hd_image_url(url: str) -> str:
    """Upgrade a mobile.de CDN thumbnail URL to full-size (1600w)."""
    return re.sub(r'rule=mo-\d+w?', 'rule=mo-1600w', url)


def _parse_german_price_str(s: str) -> float | None:
    """Parse a German-formatted price string like '15.900 €' to a float."""
    cleaned = re.sub(r'[^\d,.]', '', s.strip())
    if not cleaned:
        return None
    if ',' in cleaned:
        cleaned = cleaned.replace('.', '').replace(',', '.')
    else:
        cleaned = cleaned.replace('.', '')
    try:
        return float(cleaned)
    except ValueError:
        return None


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


def _download_image(url: str) -> 'django.core.files.base.ContentFile | None':
    """Download an image URL and return a ContentFile, or None on failure."""
    from django.core.files.base import ContentFile
    try:
        resp = requests.get(url, timeout=20, headers={'User-Agent': HEADERS['User-Agent']})
        resp.raise_for_status()
        last_segment = url.split('?')[0].rsplit('/', 1)[-1]
        ext = last_segment.rsplit('.', 1)[-1] if '.' in last_segment else 'jpg'
        return ContentFile(resp.content, name=f'img.{ext}')
    except Exception as exc:
        logger.warning('Image download failed for %s: %s', url, exc)
        return None


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
        'price_vat_exempt': listing.get('price_vat_exempt', False),
        'mileage_km': listing.get('mileage_km'),
        'fuel_type': listing.get('fuel_type', ''),
        'power_hp': listing.get('power_hp'),
        'battery_capacity_kwh': listing.get('battery_capacity_kwh'),
        'color': listing.get('color', ''),
        'interior_color': listing.get('interior_color', ''),
        'equipment': listing.get('equipment', []),
        'thumbnail_url': listing.get('thumbnail_url', ''),
        'price_rating': listing.get('price_rating', ''),
        'price_rating_thresholds': listing.get('price_rating_thresholds', []),
        'country': listing.get('country', ''),
        'seller_type': listing.get('seller_type', ''),
        'is_active': True,
    }

    if dry_run:
        make_str = listing.get('make_name', '?')
        model_str = listing.get('model_name', '?')
        logger.info('[DRY] %s %s %s — %s km @ %s € [%s/%s]',
                    make_str, model_str, listing.get('trim', ''),
                    listing.get('mileage_km', '?'), listing.get('price', '?'),
                    listing.get('seller_type', '?'), listing.get('price_rating', '?'))
        return

    vehicle, created = Vehicle.objects.update_or_create(
        listing_id=listing_id,
        defaults=defaults,
    )

    # Sync images only when the URL set has changed
    image_urls = listing.get('image_urls', [])
    if image_urls:
        existing = list(vehicle.images.values_list('url', flat=True))
        if set(image_urls) != set(existing):
            vehicle.images.all().delete()
            for i, url in enumerate(image_urls):
                content_file = _download_image(url)
                img = VehicleImage(vehicle=vehicle, url=url, order=i)
                if content_file:
                    img.image.save(content_file.name, content_file, save=False)
                img.save()

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
            self.stdout.write(self.style.ERROR('  [debug] No __INITIAL_STATE__ / __NEXT_DATA__ found in page.'))
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
