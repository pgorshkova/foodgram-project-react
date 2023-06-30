import csv

from django.conf import settings
from django.core.management.base import BaseCommand

from recipes.models import Ingredient

CSV_ROOT = settings.BASE_DIR / 'data'


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        with open(
                str(CSV_ROOT) + '/ingredients.csv', encoding='utf-8'
        ) as csvfile:
            user = csv.reader(csvfile)
            for row in user:
                Ingredient.objects.get_or_create(
                    name=row[0],
                    measure=row[1]
                )
                self.stdout.write(
                    self.style.SUCCESS('Ingridient fixture loaded!')
                )
