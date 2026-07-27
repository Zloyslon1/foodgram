from recipes.models import Tag

from ._base_import import ImportFromJsonCommand


class Command(ImportFromJsonCommand):
    model = Tag
    fixture = 'tags.json'
