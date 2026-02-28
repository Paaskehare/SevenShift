from django.db import migrations
from django.db.models import BooleanField, Case, Value, When


def invert_price_vat_exempt(apps, schema_editor):
    Vehicle = apps.get_model('vehicles', 'Vehicle')
    Vehicle.objects.update(
        price_vat_exempt=Case(
            When(price_vat_exempt=True, then=Value(False)),
            When(price_vat_exempt=False, then=Value(True)),
            output_field=BooleanField(),
        )
    )


class Migration(migrations.Migration):

    dependencies = [
        ('vehicles', '0004_vehicle_country_vehicle_price_rating_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='vehicle',
            old_name='price_vat_applicable',
            new_name='price_vat_exempt',
        ),
        migrations.RunPython(invert_price_vat_exempt, migrations.RunPython.noop),
    ]
