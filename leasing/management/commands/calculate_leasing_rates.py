from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError

from leasing.models import Financing, Listing
from leasing.utils import estimate_dk_car_prices, estimate_new_car_price, estimate_used_car_value
from vehicles.models import Vehicle

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

DE_VAT = 0.19
DK_VAT = 0.25


class Command(BaseCommand):
    help = 'Calculate monthly leasing rates for vehicles using a Financing object'

    def add_arguments(self, parser):
        parser.add_argument(
            '--financing', type=int, required=True, metavar='ID',
            help='PK of the Financing object to use',
        )
        parser.add_argument('--duration', type=int, default=12, metavar='MONTHS')
        parser.add_argument('--km-per-year', type=int, default=15000, dest='km_per_year')
        parser.add_argument('--down-payment', type=float, default=0.0, dest='down_payment')
        parser.add_argument(
            '--residual-pct', type=float, default=None, dest='residual_pct',
            help='Residual value as a fraction of price at end of lease (e.g. 0.50). '
                 'If omitted, taken from estimate_dk_car_prices residual_pct.',
        )
        parser.add_argument(
            '--vehicle', type=int, default=None, metavar='ID',
            help='Only process this vehicle PK',
        )
        parser.add_argument('--limit', type=int, default=50)
        parser.add_argument('--eur-to-dkk', type=float, default=7.46, dest='eur_to_dkk')
        parser.add_argument(
            '--leasing-type', choices=['financial', 'operating'], default='financial',
            dest='leasing_type',
        )
        parser.add_argument(
            '--create', action='store_true',
            help='Persist a Listing record for each vehicle (default: dry-run)',
        )

    def handle(self, *args, **options):
        try:
            financing = Financing.objects.get(pk=options['financing'])
        except Financing.DoesNotExist:
            raise CommandError(f"Financing #{options['financing']} not found")

        self.stdout.write(
            f"Financing #{financing.pk}  "
            f"rate={float(financing.interest_rate)*100:.2f}%  "
            f"tax={float(financing.tax_interest)*100:.2f}%  "
            f"type={financing.get_rate_type_display()}"
        )
        self.stdout.write(
            f"Duration: {options['duration']} months  |  "
            f"km/year: {options['km_per_year']:,}  |  "
            f"Down payment: {options['down_payment']:,.0f} DKK  |  "
            f"{'CREATING LISTINGS' if options['create'] else 'dry-run'}"
        )
        self.stdout.write('')

        qs = (
            Vehicle.objects
            .filter(is_active=True)
            .exclude(price__isnull=True)
            .exclude(first_registration__isnull=True)
            .exclude(mileage_km__isnull=True)
            .select_related('make', 'model')
        )
        if options['vehicle']:
            qs = qs.filter(pk=options['vehicle'])
        qs = qs[:options['limit']]

        COL = [30, 5, 7, 6, 12, 12, 10, 12, 14]
        HEADERS = ['Vehicle', 'Year', 'Mileage', 'Fuel', 'DK Price', 'Residual', 'Resid %', 'Prop. RegTax', 'Monthly (DKK)']

        def row(*cells):
            return '  '.join(str(c).rjust(w) for c, w in zip(cells, COL))

        self.stdout.write(row(*HEADERS))
        self.stdout.write('  '.join('-' * w for w in COL))

        created = 0
        for v in qs:
            age = v.age_months
            if age is None:
                continue

            fuel_key = FUEL_TYPE_MAP.get((v.fuel_type or '').upper(), 'petrol')
            engine_liters = round(v.displacement_cc / 1000, 1) if v.displacement_cc else None
            battery_kwh = float(v.battery_capacity_kwh) if v.battery_capacity_kwh else 0.0

            # Convert EUR listing price → DKK taxable value (exc. Danish reg tax)
            price_eur = float(v.price)
            source_vat = DE_VAT if v.country == 'DE' else (0.0 if v.price_vat_exempt else DK_VAT)
            price_eur_ex_vat = price_eur / (1 + source_vat) if source_vat else price_eur
            taxable_dkk = price_eur_ex_vat * options['eur_to_dkk'] * (1 + DK_VAT)

            try:
                est = estimate_dk_car_prices(
                    used_car_price_dkk=taxable_dkk,
                    age_months=age,
                    mileage_km=v.mileage_km,
                    fuel_type=fuel_key,
                    battery_capacity_kwh=battery_kwh,
                    engine_liters=engine_liters,
                )
            except Exception as e:
                self.stderr.write(f'  [{v}] estimate failed: {e}')
                continue

            # Listing price: EUR → DKK, ex source VAT, no DK VAT added
            dk_price = price_eur_ex_vat * options['eur_to_dkk']
            down_payment = options['down_payment']
            registration_tax = float(est['used_registration_tax'])

            # Residual value: project age and mileage forward to end of lease,
            # then estimate the car's value at that future point.
            if options['residual_pct'] is not None:
                residual_value = dk_price * options['residual_pct']
                residual_pct = options['residual_pct']
            else:
                # Reverse-depreciate dk_price back to an implied new-car price,
                # then re-depreciate forward to end of lease. This keeps the
                # residual anchored to dk_price, not the inflated DK retail price.
                implied_new = estimate_new_car_price(
                    dk_price, age, v.mileage_km, fuel_type=fuel_key, engine_liters=engine_liters,
                )
                end_age = age + options['duration']
                end_km = v.mileage_km + options['km_per_year'] * options['duration'] // 12
                residual_value = estimate_used_car_value(
                    implied_new, end_age, end_km, fuel_type=fuel_key, engine_liters=engine_liters,
                )
                residual_pct = residual_value / dk_price

            prop_reg_tax = financing.calculate_proportional_registration_tax(
                registration_tax=registration_tax,
                car_age_months=age,
                duration_months=options['duration'],
            )

            monthly = financing.calculate_monthly_payment(
                price=dk_price,
                down_payment=down_payment,
                residual_value=residual_value,
                duration_months=options['duration'],
                registration_tax=prop_reg_tax,
            )

            label = str(v)[:COL[0]]
            self.stdout.write(row(
                label,
                v.year or '',
                f'{v.mileage_km:,}',
                v.fuel_type or '',
                f'{dk_price:,.0f}',
                f'{residual_value:,.0f}',
                f'{residual_pct*100:.1f}%',
                f'{prop_reg_tax:,.0f}',
                f'{monthly:,.0f}',
            ))

            if options['create']:
                Listing.objects.create(
                    vehicle=v,
                    financing=financing,
                    price=Decimal(str(round(dk_price, 2))),
                    currency='DKK',
                    registration_tax=Decimal(str(round(registration_tax, 2))),
                    mileage=v.mileage_km,
                    km_per_year=options['km_per_year'],
                    residual_value=Decimal(str(round(residual_value, 2))),
                    residual_deprecation_pct=Decimal(str(round(1 - residual_pct, 4))),
                    down_payment=Decimal(str(round(down_payment, 2))),
                    monthly_payment=Decimal(str(round(monthly, 2))),
                    duration_months=options['duration'],
                    leasing_type=options['leasing_type'],
                )
                created += 1

        if options['create']:
            self.stdout.write(self.style.SUCCESS(f'\nCreated {created} listing(s).'))
