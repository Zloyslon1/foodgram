from django.utils import timezone


def render_shopping_list(products, recipes):
    """Текст списка покупок: продукты и рецепты, для которых они нужны."""
    return '\n'.join([
        f'Список покупок, составлен {timezone.localdate():%d.%m.%Y}',
        '',
        'Продукты:',
        *[
            f'{number}. {product["product__name"].capitalize()} '
            f'({product["product__measurement_unit"]}) — {product["total"]}'
            for number, product in enumerate(products, start=1)
        ],
        '',
        'Рецепты:',
        *[
            f'{number}. {recipe.name} (автор: {recipe.author.username})'
            for number, recipe in enumerate(recipes, start=1)
        ],
    ])
