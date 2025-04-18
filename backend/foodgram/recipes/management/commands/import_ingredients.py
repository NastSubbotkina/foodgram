import csv
import os

from django.core.management.base import BaseCommand

from foodgram import settings
from recipes.models import Ingredient


class Command(BaseCommand):
    help = 'Import ingredients from a fixed CSV file'

    def handle(self, *args, **kwargs):
        csv_file_path = os.path.join(
            settings.BASE_DIR, 'data', 'ingredients.csv')

        with open(csv_file_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                name = row[0]
                measurement_unit = row[1]
                ingredient = Ingredient(
                    name=name,
                    measurement_unit=measurement_unit,
                )
                ingredient.save()
            self.stdout.write('Successfully imported ingredients')
