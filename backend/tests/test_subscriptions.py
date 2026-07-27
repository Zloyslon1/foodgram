import pytest

from .conftest import make_recipe


@pytest.fixture
def author_with_recipes(other_user, tags, products):
    for index in range(2):
        make_recipe(
            other_user,
            tags[:1],
            [(products[0], 1)],
            name=f'Рецепт Маши {index}',
        )
    return other_user


def test_subscribe(auth_api, author_with_recipes):
    response = auth_api.post(
        f'/api/users/{author_with_recipes.id}/subscribe/'
    )
    assert response.status_code == 201
    assert response.data['is_subscribed'] is True
    assert response.data['recipes_count'] == 2
    assert len(response.data['recipes']) == 2


def test_subscribe_to_self_returns_400(auth_api, user):
    assert auth_api.post(f'/api/users/{user.id}/subscribe/').status_code == 400


def test_subscribe_twice_returns_400(auth_api, other_user):
    auth_api.post(f'/api/users/{other_user.id}/subscribe/')
    response = auth_api.post(f'/api/users/{other_user.id}/subscribe/')
    assert response.status_code == 400


@pytest.mark.django_db
def test_subscribe_to_missing_user_returns_404(auth_api):
    assert auth_api.post('/api/users/9876/subscribe/').status_code == 404


@pytest.mark.django_db
def test_subscribe_requires_auth(api, other_user):
    response = api.post(f'/api/users/{other_user.id}/subscribe/')
    assert response.status_code == 401


def test_subscriptions_list(auth_api, author_with_recipes):
    auth_api.post(f'/api/users/{author_with_recipes.id}/subscribe/')
    response = auth_api.get('/api/users/subscriptions/')
    assert response.status_code == 200
    assert response.data['count'] == 1
    author = response.data['results'][0]
    assert author['username'] == author_with_recipes.username
    assert author['recipes_count'] == 2


def test_subscriptions_recipes_limit(auth_api, author_with_recipes):
    auth_api.post(f'/api/users/{author_with_recipes.id}/subscribe/')
    response = auth_api.get('/api/users/subscriptions/?recipes_limit=1')
    assert len(response.data['results'][0]['recipes']) == 1
    assert response.data['results'][0]['recipes_count'] == 2


def test_unsubscribe(auth_api, other_user):
    auth_api.post(f'/api/users/{other_user.id}/subscribe/')
    response = auth_api.delete(f'/api/users/{other_user.id}/subscribe/')
    assert response.status_code == 204
    assert auth_api.get('/api/users/subscriptions/').data['count'] == 0


def test_unsubscribe_without_subscription_returns_404(
    auth_api, other_user
):
    response = auth_api.delete(f'/api/users/{other_user.id}/subscribe/')
    assert response.status_code == 404
