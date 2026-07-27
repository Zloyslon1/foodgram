from recipes.models import Product

from ._base_import import ImportFromJsonCommand


class Command(ImportFromJsonCommand):
    model = Product
    fixture = 'ingredients.json'
