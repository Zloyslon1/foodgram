from recipes.models import Tag

from .base_import import ImportFromJsonCommand


class Command(ImportFromJsonCommand):
    model = Tag
    fixture = 'tags.json'
