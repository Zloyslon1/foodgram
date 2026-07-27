import base64

import pytest
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from rest_framework.test import APIClient

from recipes.models import Ingredient, Recipe, RecipeIngredient, Tag

User = get_user_model()

PNG_BASE64 = (
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABAgMAAABieywaAAAACVBMVEUAAAD///9fX1/S0'
    'ecCAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAACklEQVQImWNoAAAAggCByxOyYQAAAABJRU'
    '5ErkJggg=='
)
BASE64_IMAGE = f'data:image/png;base64,{PNG_BASE64}'
PASSWORD = 'StrongPass123'


@pytest.fixture(autouse=True)
def media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username='vasya',
        email='vasya@test.local',
        password=PASSWORD,
        first_name='Вася',
        last_name='Иванов',
    )


@pytest.fixture
def other_user(db):
    return User.objects.create_user(
        username='masha',
        email='masha@test.local',
        password=PASSWORD,
        first_name='Маша',
        last_name='Петрова',
    )


@pytest.fixture
def auth_api(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


@pytest.fixture
def other_auth_api(other_user):
    client = APIClient()
    client.force_authenticate(other_user)
    return client


@pytest.fixture
def tags(db):
    return [
        Tag.objects.create(name='Завтрак', slug='breakfast'),
        Tag.objects.create(name='Обед', slug='lunch'),
        Tag.objects.create(name='Ужин', slug='dinner'),
    ]


@pytest.fixture
def ingredients(db):
    return [
        Ingredient.objects.create(name='капуста', measurement_unit='г'),
        Ingredient.objects.create(name='картофель', measurement_unit='г'),
        Ingredient.objects.create(name='молоко', measurement_unit='мл'),
    ]


def make_recipe(author, tags, ingredient_amounts, name='Рецепт'):
    recipe = Recipe.objects.create(
        author=author,
        name=name,
        text='Описание',
        cooking_time=10,
        image=ContentFile(base64.b64decode(PNG_BASE64), name='r.png'),
    )
    recipe.tags.set(tags)
    RecipeIngredient.objects.bulk_create(
        RecipeIngredient(
            recipe=recipe, ingredient=ingredient, amount=amount
        )
        for ingredient, amount in ingredient_amounts
    )
    return recipe


@pytest.fixture
def recipe(user, tags, ingredients):
    return make_recipe(
        user, tags[:1], [(ingredients[0], 100)], name='Борщ'
    )


@pytest.fixture
def recipe_payload(tags, ingredients):
    return {
        'ingredients': [{'id': ingredients[0].id, 'amount': 10}],
        'tags': [tags[0].id],
        'image': BASE64_IMAGE,
        'name': 'Новый рецепт',
        'text': 'Как готовить',
        'cooking_time': 5,
    }
