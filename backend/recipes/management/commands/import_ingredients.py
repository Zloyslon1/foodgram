import csv

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from recipes.models import Ingredient

DEFAULT_CSV_PATH = settings.BASE_DIR / 'data' / 'ingredients.csv'


class Command(BaseCommand):
    help = 'Импортирует ингредиенты из CSV-файла (название,единица).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--path',
            default=str(DEFAULT_CSV_PATH),
            help='Путь к CSV-файлу с ингредиентами',
        )

    def handle(self, *args, **options):
        path = options['path']
        try:
            with open(path, encoding='utf-8') as csv_file:
                ingredients = [
                    Ingredient(name=row[0], measurement_unit=row[1])
                    for row in csv.reader(csv_file)
                    if row
                ]
        except (OSError, IndexError) as error:
            raise CommandError(
                f'Не удалось прочитать файл {path}: {error}'
            )
        Ingredient.objects.bulk_create(ingredients, ignore_conflicts=True)
        self.stdout.write(
            self.style.SUCCESS(
                f'Импорт завершён, в базе {Ingredient.objects.count()} '
                'ингредиентов.'
            )
        )
