"""
Management command: redownload_images

Deletes locally stored image files for all VehicleImage records and
re-downloads them from their original source URLs.

Usage
─────
  python manage.py redownload_images
  python manage.py redownload_images --vehicle 42   # only one vehicle
"""

from django.core.management.base import BaseCommand

from vehicles.models import VehicleImage
from vehicles.management.commands.scrape_mobile_de import _download_image


class Command(BaseCommand):
    help = 'Re-download all vehicle images from their source URLs.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--vehicle',
            type=int,
            metavar='ID',
            help='Limit to images belonging to this Vehicle ID.',
        )

    def handle(self, *args, **options):
        qs = VehicleImage.objects.all()
        if options.get('vehicle'):
            qs = qs.filter(vehicle_id=options['vehicle'])

        total = qs.count()
        self.stdout.write(f'Redownloading {total} image(s)…')

        ok = fail = 0
        for img in qs.iterator():
            if img.image:
                img.image.delete(save=False)

            cf = _download_image(img.url)
            if cf:
                img.image.save(cf.name, cf, save=True)
                ok += 1
            else:
                img.image = None
                img.save(update_fields=['image'])
                fail += 1

        self.stdout.write(self.style.SUCCESS(f'Done. {ok} OK, {fail} failed.'))
