from collections import Counter

from django.db import transaction
from djoser.serializers import UserSerializer as DjoserUserSerializer
from rest_framework import serializers

from recipes.constants import MIN_COOKING_TIME, MIN_PRODUCT_AMOUNT
from recipes.models import (
    Favorite,
    Product,
    Recipe,
    RecipeProduct,
    ShoppingCart,
    Subscription,
    Tag,
    User,
)
from .fields import Base64ImageField


def find_duplicates(items):
    """Возвращает элементы, которые встретились больше одного раза."""
    return [item for item, count in Counter(items).items() if count > 1]


class UserSerializer(DjoserUserSerializer):
    """Пользователь: поля Djoser плюс подписка и аватар."""

    is_subscribed = serializers.SerializerMethodField()

    class Meta(DjoserUserSerializer.Meta):
        fields = (
            *DjoserUserSerializer.Meta.fields,
            'is_subscribed',
            'avatar',
        )
        read_only_fields = fields

    def get_is_subscribed(self, author):
        request = self.context.get('request')
        return (
            request
            and request.user.is_authenticated
            and Subscription.objects.filter(
                user=request.user, author=author
            ).exists()
        )


class AvatarSerializer(serializers.ModelSerializer):
    """Загрузка и удаление аватара."""

    avatar = Base64ImageField()

    class Meta:
        model = User
        fields = ('avatar',)


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ('id', 'name', 'measurement_unit')


class RecipeProductReadSerializer(serializers.ModelSerializer):
    """Продукт внутри рецепта с мерой."""

    id = serializers.IntegerField(source='product.id', read_only=True)
    name = serializers.CharField(source='product.name', read_only=True)
    measurement_unit = serializers.CharField(
        source='product.measurement_unit', read_only=True
    )

    class Meta:
        model = RecipeProduct
        fields = ('id', 'name', 'measurement_unit', 'amount')
        read_only_fields = fields


class RecipeReadSerializer(serializers.ModelSerializer):
    """Рецепт для чтения — формат ответа по спецификации."""

    tags = TagSerializer(many=True, read_only=True)
    author = UserSerializer(read_only=True)
    ingredients = RecipeProductReadSerializer(
        many=True, source='recipe_products', read_only=True
    )
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            'id',
            'tags',
            'author',
            'ingredients',
            'is_favorited',
            'is_in_shopping_cart',
            'name',
            'image',
            'text',
            'cooking_time',
        )
        read_only_fields = fields

    def _has_relation(self, recipe, model):
        request = self.context.get('request')
        return (
            request
            and request.user.is_authenticated
            and model.objects.filter(
                user=request.user, recipe=recipe
            ).exists()
        )

    def get_is_favorited(self, recipe):
        return self._has_relation(recipe, Favorite)

    def get_is_in_shopping_cart(self, recipe):
        return self._has_relation(recipe, ShoppingCart)


class RecipeProductWriteSerializer(serializers.Serializer):
    """Элемент списка продуктов при создании рецепта."""

    id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all()
    )
    amount = serializers.IntegerField(min_value=MIN_PRODUCT_AMOUNT)


class RecipeWriteSerializer(serializers.ModelSerializer):
    """Создание и обновление рецепта."""

    ingredients = RecipeProductWriteSerializer(
        many=True, allow_empty=False
    )
    tags = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Tag.objects.all(), allow_empty=False
    )
    image = Base64ImageField()
    cooking_time = serializers.IntegerField(min_value=MIN_COOKING_TIME)

    class Meta:
        model = Recipe
        fields = (
            'ingredients',
            'tags',
            'image',
            'name',
            'text',
            'cooking_time',
        )

    @staticmethod
    def _validate_no_duplicates(field_name, items):
        if not items:
            raise serializers.ValidationError(
                {field_name: 'Обязательное поле.'}
            )
        duplicates = find_duplicates(items)
        if duplicates:
            raise serializers.ValidationError(
                {field_name: f'Повторяются: {duplicates}.'}
            )

    def validate(self, data):
        self._validate_no_duplicates(
            'ingredients',
            [product['id'] for product in data.get('ingredients') or ()],
        )
        self._validate_no_duplicates('tags', data.get('tags'))
        return data

    @staticmethod
    def _write_products(recipe, products):
        RecipeProduct.objects.bulk_create(
            RecipeProduct(
                recipe=recipe,
                product=product['id'],
                amount=product['amount'],
            )
            for product in products
        )

    @transaction.atomic
    def create(self, validated_data):
        products = validated_data.pop('ingredients')
        recipe = super().create(validated_data)
        self._write_products(recipe, products)
        return recipe

    @transaction.atomic
    def update(self, recipe, validated_data):
        recipe.recipe_products.all().delete()
        self._write_products(recipe, validated_data.pop('ingredients'))
        return super().update(recipe, validated_data)

    def to_representation(self, recipe):
        return RecipeReadSerializer(recipe, context=self.context).data


class RecipeShortReadSerializer(serializers.ModelSerializer):
    """Краткий рецепт для избранного, корзины и подписок."""

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')
        read_only_fields = fields


class UserWithRecipesSerializer(UserSerializer):
    """Автор с его рецептами и их количеством."""

    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(
        source='recipes.count', read_only=True
    )

    class Meta(UserSerializer.Meta):
        fields = (*UserSerializer.Meta.fields, 'recipes', 'recipes_count')
        read_only_fields = fields

    def get_recipes(self, author):
        return RecipeShortReadSerializer(
            author.recipes.all()[:int(
                self.context.get('request').GET.get(
                    'recipes_limit', 10 ** 10
                )
            )],
            many=True,
            context=self.context,
        ).data
