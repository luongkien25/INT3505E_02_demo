import copy
import pytest

from app import app, users as users_list


@pytest.fixture
def client():
    app.config['TESTING'] = True
    client = app.test_client()
    # Preserve original users list and restore after test
    original = copy.deepcopy(users_list)
    yield client
    users_list.clear()
    users_list.extend(original)


def test_get_users(client):
    rv = client.get('/users')
    assert rv.status_code == 200
    data = rv.get_json()
    assert isinstance(data, list)
    assert len(data) == 2


def test_create_user(client):
    new = {"id": 3, "name": "Alice", "email": "alice@example.com"}
    rv = client.post('/users', json=new)
    assert rv.status_code == 201
    assert rv.get_json() == new
    rv2 = client.get('/users')
    assert any(u['id'] == 3 for u in rv2.get_json())


def test_update_user_success(client):
    update = {"name": "John Smith"}
    rv = client.put('/users/1', json=update)
    assert rv.status_code == 200
    data = rv.get_json()
    assert data['name'] == "John Smith"


def test_update_user_not_found(client):
    rv = client.put('/users/999', json={"name": "X"})
    assert rv.status_code == 404
    assert 'error' in rv.get_json()


def test_delete_user_success(client):
    rv = client.delete('/users/2')
    assert rv.status_code == 204
    rv2 = client.get('/users')
    assert not any(u['id'] == 2 for u in rv2.get_json())


def test_delete_user_not_found(client):
    rv = client.delete('/users/999')
    assert rv.status_code == 404
    assert 'error' in rv.get_json()
