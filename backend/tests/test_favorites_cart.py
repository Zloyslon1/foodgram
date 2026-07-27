import re

import pytest

from .conftest import make_recipe

RELATION_URLS = ['favorite', 'shopping_cart']


@pytest.mark.parametrize('relation', RELATION_URLS)
def test_add_recipe_to_relation(auth_api, recipe, relation):
    response = auth_api.post(f'/api/recipes/{recipe.id}/{relation}/')
    assert response.status_code == 201
    assert set(response.data.keys()) == {
        'id', 'name', 'image', 'cooking_time'
    }


@pytest.mark.parametrize('relation', RELATION_URLS)
def test_add_recipe_twice_returns_400(auth_api, recipe, relation):
    auth_api.post(f'/api/recipes/{recipe.id}/{relation}/')
    response = auth_api.post(f'/api/recipes/{recipe.id}/{relation}/')
    assert response.status_code == 400


@pytest.mark.django_db
@pytest.mark.parametrize('relation', RELATION_URLS)
def test_add_missing_recipe_returns_404(auth_api, relation):
    assert auth_api.post(f'/api/recipes/9876/{relation}/').status_code == 404


@pytest.mark.parametrize('relation', RELATION_URLS)
def test_remove_recipe_from_relation(auth_api, recipe, relation):
    auth_api.post(f'/api/recipes/{recipe.id}/{relation}/')
    response = auth_api.delete(f'/api/recipes/{recipe.id}/{relation}/')
    assert response.status_code == 204


@pytest.mark.parametrize('relation', RELATION_URLS)
def test_remove_not_added_recipe_returns_404(auth_api, recipe, relation):
    response = auth_api.delete(f'/api/recipes/{recipe.id}/{relation}/')
    assert response.status_code == 404


@pytest.mark.django_db
@pytest.mark.parametrize('relation', RELATION_URLS)
def test_relation_requires_auth(api, recipe, relation):
    assert api.post(f'/api/recipes/{recipe.id}/{relation}/').status_code == 401


def test_download_shopping_cart_sums_ingredients(
    auth_api, user, tags, products
):
    first = make_recipe(
        user,
        tags[:1],
        [(products[0], 100), (products[2], 30)],
        name='Первый',
    )
    second = make_recipe(
        user, tags[:1], [(products[0], 50)], name='Второй'
    )
    for recipe in (first, second):
        auth_api.post(f'/api/recipes/{recipe.id}/shopping_cart/')

    response = auth_api.get('/api/recipes/download_shopping_cart/')
    assert response.status_code == 200

    content = b''.join(response.streaming_content).decode('utf-8')
    parsed = {}
    for line in content.splitlines():
        match = re.match(r'^\d+\. (.+) \((.+)\) — (\d+)$', line)
        if match:
            parsed[match.group(1)] = int(match.group(3))
    assert parsed == {'Капуста': 150, 'Молоко': 30}
    assert 'Первый' in content and 'Второй' in content
    assert user.username in content


@pytest.mark.django_db
def test_download_shopping_cart_requires_auth(api):
    response = api.get('/api/recipes/download_shopping_cart/')
    assert response.status_code == 401
