from django.utils import timezone

PRODUCT_LINE = '{number}. {name} ({unit}) — {total}'
RECIPE_LINE = '{number}. {name} (автор: {author}, теги: {tags})'


def render_shopping_list(products, recipes):
    """Текст списка покупок: продукты и рецепты, для которых они нужны."""
    return '\n'.join([
        f'Список покупок, составлен {timezone.localdate():%d.%m.%Y}',
        '',
        'Продукты:',
        *[
            PRODUCT_LINE.format(
                number=number,
                name=product['product__name'].capitalize(),
                unit=product['product__measurement_unit'],
                total=product['total'],
            )
            for number, product in enumerate(products, start=1)
        ],
        '',
        'Рецепты:',
        *[
            RECIPE_LINE.format(
                number=number,
                name=recipe.name,
                author=recipe.author.username,
                tags=', '.join(tag.name for tag in recipe.tags.all()),
            )
            for number, recipe in enumerate(recipes, start=1)
        ],
    ])
