from flask import Flask, jsonify, request
from books import get_all_books, borrow_book, return_book
import jwt
import datetime
from functools import wraps

app = Flask(__name__)

app.config['SECRET_KEY'] = 'your_secret_key'

books_cache = None

def token_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')  

        if not token:
            return jsonify({'message': 'Token is missing!'}), 403
        
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = data['user'] 
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired!'}), 403
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Invalid token!'}), 403

        return f(current_user, *args, **kwargs)

    return decorated_function

@app.route('/api/login', methods=['POST'])
def login():
    auth = request.json

    username = auth.get('username')
    password = auth.get('password')

    if username == 'admin' and password == 'password':
        token = jwt.encode({'user': username, 'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)},
                            app.config['SECRET_KEY'], algorithm="HS256")
        return jsonify({'token': token})

    return jsonify({'message': 'Invalid credentials!'}), 401

@app.route('/api/books', methods=['GET'])
@token_required
def get_books(current_user):
    global books_cache
    if books_cache is None: 
        books_cache = get_all_books()
    return jsonify(books_cache)

@app.route('/api/borrow/<int:book_id>', methods=['POST'])
@token_required
def borrow(book_id, current_user):
    book = borrow_book(book_id)
    if book:
        global books_cache
        books_cache = None 
        return jsonify({"message": f"Sách '{book['title']}' đã được mượn thành công!"}), 200
    return jsonify({"message": "Sách không tồn tại hoặc không có sẵn!"}), 400

@app.route('/api/return/<int:book_id>', methods=['POST'])
@token_required
def return_book_api(book_id, current_user):
    book = return_book(book_id)
    if book:
        global books_cache
        books_cache = None  
        return jsonify({"message": f"Sách '{book['title']}' đã được trả thành công!"}), 200
    return jsonify({"message": "Sách không tồn tại hoặc chưa được mượn!"}), 400

@app.route('/api/code', methods=['GET'])
@token_required
def code_on_demand(current_user):
    code = """
    <script>
        alert('Hello from server!');
    </script>
    """
    return jsonify({"code": code})

if __name__ == '__main__':
    app.run(debug=True)


