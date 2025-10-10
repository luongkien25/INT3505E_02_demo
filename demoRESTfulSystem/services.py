# services.py
import hashlib
import json
from datetime import datetime

from books import (
    get_all_books,
    find_book_by_id,
    borrow_book,
    return_book,
    get_books_snapshot,
    loans
)

def list_books_service(page=1, per_page=10):
    paginated_books, total = get_all_books(page, per_page)
    return paginated_books, total

def get_book_service(book_id: int):
    return find_book_by_id(book_id)

def compute_books_etag(page, per_page):
    snapshot = get_books_snapshot()
    payload = {
        'page': page,
        'per_page': per_page,
        'snapshot': snapshot['version'],   
        'count': snapshot['count']
    }
    raw = json.dumps(payload, sort_keys=True).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()

def create_loan_service(book_id: int, borrower):
    book = find_book_by_id(book_id)
    if not book:
        return False, {'status': 404, 'message': 'Sách không tồn tại'}

    if not book['available']:
        return False, {'status': 409, 'message': 'Sách đang được mượn'}

    updated = borrow_book(book_id, borrower_id=borrower.get('id'))
    if not updated:
        return False, {'status': 400, 'message': 'Không thể mượn sách'}

    loan = next((l for l in loans if l['book_id'] == book_id and l['returned_at'] is None), None)
    return True, {'loan': loan}

def delete_loan_service(book_id: int, borrower):
    book = find_book_by_id(book_id)
    if not book:
        return False, {'status': 404, 'message': 'Sách không tồn tại'}

    active_loan = next((l for l in loans if l['book_id'] == book_id and l['returned_at'] is None), None)
    if not active_loan:
        return False, {'status': 409, 'message': 'Sách chưa được mượn'}

    ok = return_book(book_id)
    if not ok:
        return False, {'status': 400, 'message': 'Không thể trả sách'}
    return True, {}

def list_loans_service():
    return loans
