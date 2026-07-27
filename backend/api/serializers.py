from django.contrib.auth import get_user_model
from django.db import transaction
from djoser.serializers import UserCreateSerializer as DjoserUserCreate
from rest_framework import serializers

from recipes.constants import MIN_INGREDIENT_AMOUNT
from recipes.models import Ingredient, Recipe, RecipeIngredient, Tag

from .fields import Base64ImageField

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Пользователь с полями по спецификации."""

    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'avatar',
        )

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        if not hasattr(request, 'subscribed_author_ids'):
            request.subscribed_author_ids = set(
                request.user.subscriptions.values_list(
                    'author_id', flat=True
                )
            )
        return obj.pk in request.subscribed_author_ids


class UserCreateSerializer(DjoserUserCreate):
    """Регистрация: в ответе нет is_subscribed и avatar."""

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'password',
        )


class AvatarSerializer(serializers.ModelSerializer):
    avatar = Base64ImageField()

    class Meta:
        model = User
        fields = ('avatar',)


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class RecipeIngredientReadSerializer(serializers.ModelSerializer):
    """Ингредиент внутри рецепта с количеством."""

    id = serializers.IntegerField(source='ingredient.id')
    name = serializers.CharField(source='ingredient.name')
    measurement_unit = serializers.CharField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeReadSerializer(serializers.ModelSerializer):
    """Рецепт для чтения — формат ответа по спецификации."""

    tags = TagSerializer(many=True, read_only=True)
    author = UserSerializer(read_only=True)
    ingredients = RecipeIngredientReadSerializer(
        many=True, source='recipe_ingredients', read_only=True
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

    def _check_relation(self, obj, annotation, related_manager):
        if hasattr(obj, annotation):
            return getattr(obj, annotation)
        request = self.context.get('request')
        return bool(
            request
            and request.user.is_authenticated
            and related_manager.filter(user=request.user).exists()
        )

    def get_is_favorited(self, obj):
        return self._check_relation(obj, 'is_favorited', obj.favorites)

    def get_is_in_shopping_cart(self, obj):
        return self._check_relation(
            obj, 'is_in_shopping_cart', obj.shoppingcarts
        )


class RecipeIngredientWriteSerializer(serializers.Serializer):
    """Элемент списка ингредиентов при создании рецепта."""

    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all()
    )
    amount = serializers.IntegerField(min_value=MIN_INGREDIENT_AMOUNT)


class RecipeWriteSerializer(serializers.ModelSerializer):
    """Создание и обновление рецепта."""

    ingredients = RecipeIngredientWriteSerializer(
        many=True, allow_empty=False
    )
    tags = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Tag.objects.all(), allow_empty=False
    )
    image = Base64ImageField()

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

    def validate(self, data):
        ingredients = data.get('ingredients')
        if ingredients is None:
            raise serializers.ValidationError(
                {'ingredients': 'Обязательное поле.'}
            )
        ingredient_ids = [item['id'] for item in ingredients]
        if len(ingredient_ids) != len(set(ingredient_ids)):
            raise serializers.ValidationError(
                {'ingredients': 'Ингредиенты не должны повторяться.'}
            )
        tags = data.get('tags')
        if tags is None:
            raise serializers.ValidationError(
                {'tags': 'Обязательное поле.'}
            )
        if len(tags) != len(set(tags)):
            raise serializers.ValidationError(
                {'tags': 'Теги не должны повторяться.'}
            )
        return data

    @staticmethod
    def _write_ingredients(recipe, ingredients):
        RecipeIngredient.objects.bulk_create(
            RecipeIngredient(
                recipe=recipe,
                ingredient=item['id'],
                amount=item['amount'],
            )
            for item in ingredients
        )

    def create(self, validated_data):
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        with transaction.atomic():
            recipe = Recipe.objects.create(**validated_data)
            recipe.tags.set(tags)
            self._write_ingredients(recipe, ingredients)
        return recipe

    def update(self, instance, validated_data):
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        old_image = (
            instance.image.name if 'image' in validated_data else ''
        )
        with transaction.atomic():
            instance = super().update(instance, validated_data)
            instance.tags.set(tags)
            instance.recipe_ingredients.all().delete()
            self._write_ingredients(instance, ingredients)
        if old_image and old_image != instance.image.name:
            instance.image.storage.delete(old_image)
        return instance

    def to_representation(self, instance):
        return RecipeReadSerializer(instance, context=self.context).data


class RecipeMinifiedSerializer(serializers.ModelSerializer):
    """Краткий рецепт для избранного, корзины и подписок."""

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class SubscriptionSerializer(UserSerializer):
    """Автор с рецептами и их количеством."""

    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ('recipes', 'recipes_count')

    def get_recipes(self, obj):
        request = self.context.get('request')
        recipes = list(obj.recipes.all())
        recipes_limit = (
            request.query_params.get('recipes_limit') if request else None
        )
        if recipes_limit and recipes_limit.isdigit():
            recipes = recipes[:int(recipes_limit)]
        return RecipeMinifiedSerializer(
            recipes, many=True, context=self.context
        ).data

    def get_recipes_count(self, obj):
        if hasattr(obj, 'recipes_count'):
            return obj.recipes_count
        return obj.recipes.count()
