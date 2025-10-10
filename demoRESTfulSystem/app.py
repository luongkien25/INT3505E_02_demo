# app.py
from flask import Flask, jsonify, request, make_response, url_for
from functools import wraps
import datetime
import hashlib
import jwt

from services import (
    list_books_service,
    get_book_service,
    create_loan_service,
    delete_loan_service,
    list_loans_service,
    compute_books_etag
)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'  

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            return jsonify({'message': 'Missing or invalid Authorization header. Use Bearer <token>.'}), 401

        token = parts[1]
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = data['user']  
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Invalid token!'}), 401

        return f(current_user, *args, **kwargs)
    return decorated

def set_pagination_headers(resp, page, per_page, total_items):
    total_pages = (total_items // per_page) + (1 if total_items % per_page else 0)
    resp.headers['Total-Count'] = total_items
    resp.headers['Page'] = page
    resp.headers['Per-Page'] = per_page
    resp.headers['Total-Pages'] = total_pages
    return resp

def apply_cache_headers(resp, etag, max_age=30):
    resp.headers['ETag'] = etag
    resp.headers['Cache-Control'] = f'public, max-age={max_age}'
    return resp

@app.route('/api/books', methods=['GET'])
@token_required
def list_books(current_user):
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    books_slice, total = list_books_service(page, per_page)

    etag = compute_books_etag(page, per_page)
    if_none_match = request.headers.get('If-None-Match')
    if if_none_match == etag:
        resp = make_response('', 304)
        resp = apply_cache_headers(resp, etag)
        return resp

    for b in books_slice:
        b['links'] = {
            'self': url_for('get_book', book_id=b['id'], _external=True),
            'loan': url_for('create_loan', book_id=b['id'], _external=True)
        }

    resp = make_response(jsonify(books_slice), 200)
    resp = set_pagination_headers(resp, page, per_page, total)
    resp = apply_cache_headers(resp, etag)
    return resp

@app.route('/api/books/<int:book_id>', methods=['GET'])
@token_required
def get_book(current_user, book_id):
    book = get_book_service(book_id)
    if not book:
        return jsonify({'message': 'Không tìm thấy sách'}), 404

    etag_src = f"{book['id']}|{book['title']}|{book['author']}|{book['available']}|{book['updated_at']}"
    etag = hashlib.sha256(etag_src.encode('utf-8')).hexdigest()
    if request.headers.get('If-None-Match') == etag:
        resp = make_response('', 304)
        return apply_cache_headers(resp, etag)

    book['links'] = {
        'self': url_for('get_book', book_id=book['id'], _external=True),
        'loan': url_for('create_loan', book_id=book['id'], _external=True),
        'loans': url_for('list_loans', _external=True)
    }
    resp = make_response(jsonify(book), 200)
    return apply_cache_headers(resp, etag, max_age=60)

@app.route('/api/loans', methods=['GET'])
@token_required
def list_loans(current_user):
    loans = list_loans_service()
    for ln in loans:
        ln['links'] = {
            'self': url_for('delete_loan', book_id=ln['book_id'], _external=True),
            'book': url_for('get_book', book_id=ln['book_id'], _external=True)
        }
    return jsonify(loans), 200

@app.route('/api/books/<int:book_id>/loan', methods=['POST'])
@token_required
def create_loan(current_user, book_id):
    ok, result = create_loan_service(book_id, borrower=current_user)
    if not ok:
        return jsonify({'message': result['message']}), result.get('status', 400)

    loan = result['loan']
    location = url_for('delete_loan', book_id=loan['book_id'], _external=True)
    loan['links'] = {
        'self': location,
        'book': url_for('get_book', book_id=loan['book_id'], _external=True)
    }
    resp = make_response(jsonify(loan), 201)
    resp.headers['Location'] = location
    return resp

@app.route('/api/books/<int:book_id>/loan', methods=['DELETE'])
@token_required
def delete_loan(current_user, book_id):
    ok, result = delete_loan_service(book_id, borrower=current_user)
    if not ok:
        return jsonify({'message': result['message']}), result.get('status', 400)
    return '', 204

@app.route('/api/code', methods=['GET'])
@token_required
def code_on_demand(current_user):
    js = "alert('Hello from server!');"
    resp = make_response(js, 200)
    resp.headers['Content-Type'] = 'application/javascript'
    resp.headers['Cache-Control'] = 'public, max-age=60'
    return resp

if __name__ == '__main__':
    app.run(debug=True)
