from flask import Flask, request, jsonify

app = Flask(__name__)

users = [
    {"id": 1, "name": "John Doe", "email": "john.doe@example.com"},
    {"id": 2, "name": "Jane Doe", "email": "jane.doe@example.com"}
]

@app.route('/users', methods=['GET'])
def get_users():
    return jsonify(users), 200

@app.route('/users', methods=['POST'])
def create_user():
    new_user = request.get_json()
    users.append(new_user)
    return jsonify(new_user), 201

@app.route('/users/<int:id>', methods=['PUT'])
def update_user(id):
    user = next((user for user in users if user["id"] == id), None)
    if user is None:
        return jsonify({"error": "User not found"}), 404
    data = request.get_json()
    user.update(data)
    return jsonify(user), 200

@app.route('/users/<int:id>', methods=['DELETE'])
def delete_user(id):
    user = next((user for user in users if user["id"] == id), None)
    if user is None:
        return jsonify({"error": "User not found"}), 404
    users.remove(user)
    return '', 204

if __name__ == '__main__':
    app.run(debug=True)

from flask import Flask, request, jsonify

app = Flask(__name__)

users = [
    {"id": 1, "name": "John Doe", "email": "john.doe@example.com"},
    {"id": 2, "name": "Jane Doe", "email": "jane.doe@example.com"}
]

@app.route('/users', methods=['GET'])
def get_users():
    return jsonify(users), 200

@app.route('/users', methods=['POST'])
def create_user():
    new_user = request.get_json()
    users.append(new_user)
    return jsonify(new_user), 201

@app.route('/users/<int:id>', methods=['PUT'])
def update_user(id):
    user = next((user for user in users if user["id"] == id), None)
    if user is None:
        return jsonify({"error": "User not found"}), 404
    data = request.get_json()
    user.update(data)
    return jsonify(user), 200

@app.route('/users/<int:id>', methods=['DELETE'])
def delete_user(id):
    user = next((user for user in users if user["id"] == id), None)
    if user is None:
        return jsonify({"error": "User not found"}), 404
    users.remove(user)
    return '', 204

if __name__ == '__main__':
    app.run(debug=True)
