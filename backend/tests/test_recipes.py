import pytest

from recipes.models import Recipe

from .conftest import make_recipe


@pytest.mark.django_db
def test_recipe_list_available_to_anonymous(api, recipe):
    response = api.get('/api/recipes/')
    assert response.status_code == 200
    assert response.data['count'] == 1


def test_create_recipe(auth_api, user, recipe_payload):
    response = auth_api.post(
        '/api/recipes/', recipe_payload, format='json'
    )
    assert response.status_code == 201
    data = response.data
    assert data['author']['username'] == user.username
    assert not data['is_favorited']
    assert not data['is_in_shopping_cart']
    assert data['ingredients'][0]['amount'] == 10
    assert data['tags'][0]['slug'] == 'breakfast'
    assert data['image'].startswith('http')


@pytest.mark.django_db
def test_create_recipe_requires_auth(api, recipe_payload):
    response = api.post('/api/recipes/', recipe_payload, format='json')
    assert response.status_code == 401


@pytest.mark.parametrize(
    'broken',
    [
        {'ingredients': None},
        {'ingredients': []},
        {'ingredients': [{'id': 9876, 'amount': 1}]},
        {'ingredients': [{'id': 'first', 'amount': 0}]},
        {'ingredients': 'duplicate'},
        {'tags': None},
        {'tags': []},
        {'tags': [9876]},
        {'tags': 'duplicate'},
        {'image': None},
        {'image': ''},
        {'name': ''},
        {'name': 'x' * 257},
        {'text': ''},
        {'cooking_time': 0},
        {'cooking_time': ''},
    ],
)
def test_create_recipe_invalid_data(
    auth_api, recipe_payload, products, tags, broken
):
    payload = dict(recipe_payload)
    for field, value in broken.items():
        if value is None:
            del payload[field]
        elif value == 'duplicate':
            payload[field] = payload[field] * 2
        elif field == 'ingredients' and value and value[0]['id'] == 'first':
            payload[field] = [{'id': products[0].id, 'amount': 0}]
        else:
            payload[field] = value
    response = auth_api.post('/api/recipes/', payload, format='json')
    assert response.status_code == 400


def test_author_can_update_recipe(auth_api, recipe, products, tags):
    payload = {
        'ingredients': [{'id': products[1].id, 'amount': 55}],
        'tags': [tags[1].id],
        'name': 'Борщ обновлённый',
        'text': 'Новое описание',
        'cooking_time': 42,
    }
    response = auth_api.patch(
        f'/api/recipes/{recipe.id}/', payload, format='json'
    )
    assert response.status_code == 200
    assert response.data['name'] == 'Борщ обновлённый'
    assert len(response.data['ingredients']) == 1
    assert response.data['ingredients'][0]['amount'] == 55


@pytest.mark.parametrize('field', ['ingredients', 'tags'])
def test_update_requires_ingredients_and_tags(
    auth_api, recipe, products, tags, field
):
    payload = {
        'ingredients': [{'id': products[0].id, 'amount': 5}],
        'tags': [tags[0].id],
        'name': 'Имя',
        'text': 'Текст',
        'cooking_time': 5,
    }
    del payload[field]
    response = auth_api.patch(
        f'/api/recipes/{recipe.id}/', payload, format='json'
    )
    assert response.status_code == 400


def test_non_author_cannot_update_recipe(other_auth_api, recipe):
    response = other_auth_api.patch(
        f'/api/recipes/{recipe.id}/', {'name': 'Чужой'}, format='json'
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_anonymous_cannot_update_recipe(api, recipe):
    response = api.patch(
        f'/api/recipes/{recipe.id}/', {'name': 'Аноним'}, format='json'
    )
    assert response.status_code == 401


def test_author_can_delete_recipe(auth_api, recipe):
    assert auth_api.delete(f'/api/recipes/{recipe.id}/').status_code == 204
    assert not Recipe.objects.filter(id=recipe.id).exists()


def test_non_author_cannot_delete_recipe(other_auth_api, recipe):
    response = other_auth_api.delete(f'/api/recipes/{recipe.id}/')
    assert response.status_code == 403
    assert Recipe.objects.filter(id=recipe.id).exists()


@pytest.mark.django_db
def test_delete_missing_recipe_returns_404(auth_api):
    assert auth_api.delete('/api/recipes/9876/').status_code == 404


@pytest.mark.django_db
def test_recipes_ordered_newest_first(api, user, tags, products):
    for index in range(3):
        make_recipe(
            user, tags[:1], [(products[0], 1)], name=f'Рецепт {index}'
        )
    response = api.get('/api/recipes/')
    identifiers = [item['id'] for item in response.data['results']]
    assert identifiers == sorted(identifiers, reverse=True)


@pytest.mark.django_db
def test_pagination_limit(api, user, tags, products):
    for index in range(3):
        make_recipe(
            user, tags[:1], [(products[0], 1)], name=f'Рецепт {index}'
        )
    response = api.get('/api/recipes/?limit=2')
    assert len(response.data['results']) == 2
    assert response.data['next'] is not None
    assert response.data['count'] == 3
