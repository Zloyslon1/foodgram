import pytest

from recipes.models import Favorite, ShoppingCart

from .conftest import make_recipe


@pytest.fixture
def three_recipes(user, other_user, tags, products):
    return [
        make_recipe(
            user, [tags[0]], [(products[0], 1)], name='Завтрак у Васи'
        ),
        make_recipe(
            user, [tags[1]], [(products[1], 2)], name='Обед у Васи'
        ),
        make_recipe(
            other_user, [tags[2]], [(products[2], 3)], name='Ужин у Маши'
        ),
    ]


@pytest.mark.django_db
def test_filter_by_tags_works_as_or(api, three_recipes):
    response = api.get('/api/recipes/?tags=breakfast&tags=lunch')
    assert response.data['count'] == 2


@pytest.mark.django_db
def test_filter_by_author(api, other_user, three_recipes):
    response = api.get(f'/api/recipes/?author={other_user.id}')
    assert response.data['count'] == 1
    assert response.data['results'][0]['name'] == 'Ужин у Маши'


@pytest.mark.django_db
def test_filter_by_author_and_tags(api, user, three_recipes):
    response = api.get(
        f'/api/recipes/?author={user.id}&tags=breakfast&tags=dinner'
    )
    assert response.data['count'] == 1
    assert response.data['results'][0]['name'] == 'Завтрак у Васи'


def test_filter_is_favorited(auth_api, user, three_recipes):
    Favorite.objects.create(user=user, recipe=three_recipes[2])
    response = auth_api.get('/api/recipes/?is_favorited=1')
    assert response.data['count'] == 1
    assert response.data['results'][0]['id'] == three_recipes[2].id
    assert response.data['results'][0]['is_favorited'] is True


@pytest.mark.django_db
def test_filter_is_favorited_ignored_for_anonymous(
    api, user, three_recipes
):
    Favorite.objects.create(user=user, recipe=three_recipes[0])
    response = api.get('/api/recipes/?is_favorited=1')
    assert response.data['count'] == len(three_recipes)


def test_filter_is_in_shopping_cart(auth_api, user, three_recipes):
    ShoppingCart.objects.create(user=user, recipe=three_recipes[1])
    response = auth_api.get('/api/recipes/?is_in_shopping_cart=1')
    assert response.data['count'] == 1
    assert response.data['results'][0]['is_in_shopping_cart'] is True


@pytest.mark.django_db
def test_ingredient_search_by_name_start(api, products):
    response = api.get('/api/ingredients/?name=ка')
    names = {item['name'] for item in response.data}
    assert names == {'капуста', 'картофель'}


@pytest.mark.django_db
def test_tag_and_ingredient_lists_not_paginated(api, tags, products):
    assert isinstance(api.get('/api/tags/').data, list)
    assert isinstance(api.get('/api/ingredients/').data, list)


@pytest.mark.django_db
def test_tags_read_only(auth_api, tags):
    response = auth_api.post(
        '/api/tags/', {'name': 'Новый', 'slug': 'new'}
    )
    assert response.status_code == 405
