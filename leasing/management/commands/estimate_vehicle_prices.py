from django.core.management.base import BaseCommand

from vehicles.models import Vehicle
from leasing.utils import estimate_dk_car_prices

# Mobile.de fuel type keys → utils fuel type keys
FUEL_TYPE_MAP = {
    'PETROL': 'petrol',
    'DIESEL': 'diesel',
    'ELECTRICITY': 'ev',
    'HYBRID_PETROL': 'hybrid',
    'HYBRID_DIESEL': 'hybrid',
    'NATURAL_GAS': 'petrol',
    'LPG': 'petrol',
}

# German VAT rate assumed for DE-sourced listings
DE_VAT = 0.19
DK_VAT = 0.25


class Command(BaseCommand):
    help = 'Estimate new-car and Danish retail prices for vehicles'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=50)
        parser.add_argument('--eur-to-dkk', type=float, default=7.46, dest='eur_to_dkk')

    def handle(self, *args, **options):
        limit = options['limit']
        eur_to_dkk = options['eur_to_dkk']

        qs = (
            Vehicle.objects
            .filter(is_active=True)
            .exclude(price__isnull=True)
            .exclude(first_registration__isnull=True)
            .exclude(mileage_km__isnull=True)
            .select_related('make', 'car_model')
            [:limit]
        )

        # Column widths
        COL = [28, 5, 5, 7, 6, 10, 12, 14, 14, 12]
        HEADERS = ['Vehicle', 'Year', 'Age', 'Mileage', 'Fuel', 'Price EUR', 'Taxable DKK', 'New DK price', 'Used DK price', 'Used reg tax']

        def row(*cells):
            return '  '.join(str(c).rjust(w) for c, w in zip(cells, COL))

        self.stdout.write(row(*HEADERS))
        self.stdout.write('  '.join('-' * w for w in COL))

        for v in qs:
            age = v.age_months
            if age is None:
                continue

            fuel_key = FUEL_TYPE_MAP.get(v.fuel_type.upper() if v.fuel_type else '', 'petrol')
            engine_liters = round(v.displacement_cc / 1000, 1) if v.displacement_cc else None
            battery_kwh = float(v.battery_capacity_kwh) if v.battery_capacity_kwh else 0.0

            # Convert price to DKK taxable value (exc Danish reg tax)
            # Strip source VAT, convert to DKK, add Danish VAT
            price_eur = float(v.price)
            source_vat = DE_VAT if v.country == 'DE' else (0.0 if v.price_vat_exempt else DK_VAT)
            price_eur_ex_vat = price_eur / (1 + source_vat) if source_vat else price_eur
            taxable_dkk = price_eur_ex_vat * eur_to_dkk * (1 + DK_VAT)

            try:
                result = estimate_dk_car_prices(
                    used_car_price_dkk=taxable_dkk,
                    age_months=age,
                    mileage_km=v.mileage_km,
                    fuel_type=fuel_key,
                    battery_capacity_kwh=battery_kwh,
                    engine_liters=engine_liters,
                )
            except Exception as e:
                self.stderr.write(f'  [{v}] {e}')
                continue

            label = str(v)[:COL[0]]
            self.stdout.write(row(
                label,
                v.year or '',
                age,
                f'{v.mileage_km:,}',
                v.fuel_type or '',
                f'{price_eur:,.0f}',
                f'{taxable_dkk:,.0f}',
                f'{result["new_retail_price"]:,.0f}',
                f'{result["used_retail_price"]:,.0f}',
                f'{result["used_registration_tax"]:,.0f}',
            ))
