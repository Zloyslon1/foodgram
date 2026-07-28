import json

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

FIXTURES_DIR = settings.BASE_DIR / 'data'


class ImportFromJsonCommand(BaseCommand):
    """Базовая команда импорта записей из json-фикстуры."""

    model = None
    fixture = None

    @property
    def help(self):
        return (
            f'Импортирует {self.model._meta.verbose_name_plural} '
            f'из фикстуры {self.fixture}.'
        )

    def handle(self, *args, **options):
        path = FIXTURES_DIR / self.fixture
        try:
            with open(path, encoding='utf-8') as fixture:
                created = self.model.objects.bulk_create(
                    (self.model(**record) for record in json.load(fixture)),
                    ignore_conflicts=True,
                )
            self.stdout.write(self.style.SUCCESS(
                f'Импорт из фикстуры {path} завершён: '
                f'обработано записей {len(created)}.'
            ))
        except Exception as error:
            raise CommandError(
                f'Импорт из фикстуры {path} не удался: {error}'
            )
