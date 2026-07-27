from django_filters import rest_framework as filters

from recipes.models import Product, Recipe, Tag


class ProductFilter(filters.FilterSet):
    """Поиск продуктов по началу названия."""

    name = filters.CharFilter(lookup_expr='istartswith')

    class Meta:
        model = Product
        fields = ('name',)


class RecipeFilter(filters.FilterSet):
    """Фильтрация рецептов по автору, тегам, избранному и корзине."""

    tags = filters.ModelMultipleChoiceFilter(
        field_name='tags__slug',
        to_field_name='slug',
        queryset=Tag.objects.all(),
    )
    is_favorited = filters.NumberFilter(method='filter_is_favorited')
    is_in_shopping_cart = filters.NumberFilter(
        method='filter_is_in_shopping_cart'
    )

    class Meta:
        model = Recipe
        fields = ('author', 'tags')

    def _filter_by_relation(self, recipes, value, relation):
        user = self.request.user
        if value and user.is_authenticated:
            return recipes.filter(**{f'{relation}__user': user})
        return recipes

    def filter_is_favorited(self, recipes, name, value):
        return self._filter_by_relation(recipes, value, 'favorites')

    def filter_is_in_shopping_cart(self, recipes, name, value):
        return self._filter_by_relation(recipes, value, 'shoppingcarts')
