import os
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def create_app(config: dict | None = None):
    app = Flask(__name__)
    # allow override via env or config param
    database_url = None
    if config and 'SQLALCHEMY_DATABASE_URI' in config:
        database_url = config['SQLALCHEMY_DATABASE_URI']
    else:
        database_url = os.environ.get('DATABASE_URL', 'sqlite:///integration_test.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)

    class User(db.Model):
        __tablename__ = 'users'
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(128), nullable=False)
        email = db.Column(db.String(256), unique=True, nullable=False)

        def to_dict(self):
            return {'id': self.id, 'name': self.name, 'email': self.email}

    @app.route('/db/users', methods=['GET'])
    def get_users():
        users = User.query.all()
        return jsonify([u.to_dict() for u in users]), 200

    @app.route('/db/users', methods=['POST'])
    def create_user():
        data = request.get_json() or {}
        user = User(name=data.get('name'), email=data.get('email'))
        db.session.add(user)
        db.session.commit()
        return jsonify(user.to_dict()), 201

    @app.route('/db/users/<int:id>', methods=['PUT'])
    def update_user(id):
        user = User.query.get(id)
        if user is None:
            return jsonify({'error': 'User not found'}), 404
        data = request.get_json() or {}
        if 'name' in data:
            user.name = data['name']
        if 'email' in data:
            user.email = data['email']
        db.session.commit()
        return jsonify(user.to_dict()), 200

    @app.route('/db/users/<int:id>', methods=['DELETE'])
    def delete_user(id):
        user = User.query.get(id)
        if user is None:
            return jsonify({'error': 'User not found'}), 404
        db.session.delete(user)
        db.session.commit()
        return '', 204

    # expose model on app for tests
    app.db = db
    app.User = User
    return app


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        db.create_all()
    app.run(debug=True)
