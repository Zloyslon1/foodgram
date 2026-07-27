import pytest

from .conftest import BASE64_IMAGE, PASSWORD

REGISTRATION_DATA = {
    'email': 'new@test.local',
    'username': 'newbie',
    'first_name': 'Новый',
    'last_name': 'Пользователь',
    'password': 'StrongPass123',
}


@pytest.mark.django_db
def test_registration_creates_user(api):
    response = api.post('/api/users/', REGISTRATION_DATA)
    assert response.status_code == 201
    assert set(response.data.keys()) == {
        'email', 'id', 'username', 'first_name', 'last_name'
    }


@pytest.mark.django_db
@pytest.mark.parametrize('missing_field', REGISTRATION_DATA.keys())
def test_registration_requires_field(api, missing_field):
    data = {
        key: value for key, value in REGISTRATION_DATA.items()
        if key != missing_field
    }
    response = api.post('/api/users/', data)
    assert response.status_code == 400
    assert missing_field in response.data


@pytest.mark.django_db
def test_registration_duplicate_email(api, user):
    data = dict(REGISTRATION_DATA, email=user.email)
    assert api.post('/api/users/', data).status_code == 400


@pytest.mark.django_db
def test_token_login_and_logout(api, user):
    response = api.post(
        '/api/auth/token/login/',
        {'email': user.email, 'password': PASSWORD},
    )
    assert response.status_code == 200
    token = response.data['auth_token']

    api.credentials(HTTP_AUTHORIZATION=f'Token {token}')
    assert api.get('/api/users/me/').status_code == 200
    assert api.post('/api/auth/token/logout/').status_code == 204
    assert api.get('/api/users/me/').status_code == 401


@pytest.mark.django_db
def test_login_with_wrong_password(api, user):
    response = api.post(
        '/api/auth/token/login/',
        {'email': user.email, 'password': 'wrong-password'},
    )
    assert response.status_code == 400


def test_me_returns_profile(auth_api, user):
    response = auth_api.get('/api/users/me/')
    assert response.status_code == 200
    assert response.data['username'] == user.username
    assert not response.data['is_subscribed']
    assert response.data['avatar'] is None


@pytest.mark.django_db
def test_me_requires_auth(api):
    assert api.get('/api/users/me/').status_code == 401


@pytest.mark.django_db
def test_user_list_available_to_anonymous(api, user):
    response = api.get('/api/users/')
    assert response.status_code == 200
    assert response.data['count'] == 1


def test_user_detail_available_to_anonymous(api, user):
    assert api.get(f'/api/users/{user.id}/').status_code == 200


@pytest.mark.django_db
def test_missing_user_returns_404(auth_api):
    assert auth_api.get('/api/users/9876/').status_code == 404


def test_set_password(api, auth_api, user):
    response = auth_api.post(
        '/api/users/set_password/',
        {'current_password': PASSWORD, 'new_password': 'OtherPass456'},
    )
    assert response.status_code == 204
    login = api.post(
        '/api/auth/token/login/',
        {'email': user.email, 'password': 'OtherPass456'},
    )
    assert login.status_code == 200


def test_set_password_wrong_current(auth_api):
    response = auth_api.post(
        '/api/users/set_password/',
        {'current_password': 'wrong', 'new_password': 'OtherPass456'},
    )
    assert response.status_code == 400


def test_avatar_set_and_delete(auth_api, user):
    response = auth_api.put(
        '/api/users/me/avatar/', {'avatar': BASE64_IMAGE}
    )
    assert response.status_code == 200
    assert response.data['avatar']
    user.refresh_from_db()
    assert user.avatar

    assert auth_api.delete('/api/users/me/avatar/').status_code == 204
    user.refresh_from_db()
    assert not user.avatar


def test_avatar_empty_body(auth_api):
    assert auth_api.put('/api/users/me/avatar/', {}).status_code == 400


def test_avatar_malformed_base64(auth_api):
    response = auth_api.put(
        '/api/users/me/avatar/', {'avatar': 'data:image/pngAAAA'}
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_avatar_requires_auth(api):
    response = api.put(
        '/api/users/me/avatar/', {'avatar': BASE64_IMAGE}
    )
    assert response.status_code == 401
