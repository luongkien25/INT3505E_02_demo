import os
import tempfile
from app_db import create_app


def test_create_user_persists_to_db(tmp_path):
    db_file = tmp_path / "test_integration.db"
    db_uri = f"sqlite:///{db_file}"
    app = create_app({'SQLALCHEMY_DATABASE_URI': db_uri})
    with app.app_context():
        app.db.create_all()
        client = app.test_client()

        payload = {"name": "Integration Alice", "email": "int.alice@example.com"}
        rv = client.post('/db/users', json=payload)
        assert rv.status_code == 201
        body = rv.get_json()
        assert body['name'] == payload['name']

        # verify in DB
        user = app.User.query.filter_by(email=payload['email']).one_or_none()
        assert user is not None
        assert user.name == payload['name']
