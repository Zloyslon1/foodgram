import pytest


def test_get_link_returns_short_link(api, recipe):
    response = api.get(f'/api/recipes/{recipe.id}/get-link/')
    assert response.status_code == 200
    assert set(response.data.keys()) == {'short-link'}
    assert f'/s/{recipe.id}/' in response.data['short-link']


@pytest.mark.django_db
def test_get_link_for_missing_recipe_returns_404(api):
    assert api.get('/api/recipes/9876/get-link/').status_code == 404


def test_short_link_redirects_to_recipe(api, recipe):
    response = api.get(f'/s/{recipe.id}/')
    assert response.status_code == 302
    assert response['Location'] == f'/recipes/{recipe.id}/'


@pytest.mark.django_db
def test_unknown_short_link_returns_404(api, db):
    assert api.get('/s/9876/').status_code == 404


def test_short_link_survives_recipe_update(
    auth_api, recipe, products, tags
):
    link_before = auth_api.get(
        f'/api/recipes/{recipe.id}/get-link/'
    ).data['short-link']
    payload = {
        'ingredients': [{'id': products[1].id, 'amount': 5}],
        'tags': [tags[1].id],
        'name': 'Совсем другое имя',
        'text': 'Другой текст',
        'cooking_time': 99,
    }
    response = auth_api.patch(
        f'/api/recipes/{recipe.id}/', payload, format='json'
    )
    assert response.status_code == 200
    link_after = auth_api.get(
        f'/api/recipes/{recipe.id}/get-link/'
    ).data['short-link']
    assert link_before == link_after
