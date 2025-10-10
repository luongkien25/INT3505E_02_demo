from flask import Flask, jsonify, request, make_response
import datetime
import jwt
from functools import wraps
from services import get_books_service, borrow_book_service, return_book_service, code_on_demand_service

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

@app.route('/api/books', methods=['GET'])
@token_required
def get_books(current_user):
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)

    global books_cache
    if books_cache is None:
        books_cache, total_books = get_books_service(page, per_page)

    response = make_response(jsonify(books_cache))

    response.headers['Total-Books'] = total_books  
    response.headers['Pagination-Page'] = page  
    response.headers['Pagination-Per-Page'] = per_page  
    response.headers['Pagination-Total-Pages'] = (total_books // per_page) + (1 if total_books % per_page != 0 else 0)  # Tổng số trang

    return response

@app.route('/api/borrow/<int:book_id>', methods=['POST'])
@token_required
def borrow(book_id, current_user):
    book = borrow_book_service(book_id)
    if book:
        global books_cache
        books_cache = None  
        return jsonify({"message": f"Sách '{book['title']}' đã được mượn thành công!"}), 200
    return jsonify({"message": "Sách không tồn tại hoặc không có sẵn!"}), 400

@app.route('/api/return/<int:book_id>', methods=['POST'])
@token_required
def return_book(book_id, current_user):
    book = return_book_service(book_id)
    if book:
        global books_cache
        books_cache = None  
        return jsonify({"message": f"Sách '{book['title']}' đã được trả thành công!"}), 200
    return jsonify({"message": "Sách không tồn tại hoặc chưa được mượn!"}), 400

@app.route('/api/code', methods=['GET'])
@token_required
def code_on_demand(current_user):
    code = code_on_demand_service()
    return jsonify({"code": code})

if __name__ == '__main__':
    app.run(debug=True)
