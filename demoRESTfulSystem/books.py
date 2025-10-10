# books.py
from datetime import datetime

books = [
    {"id": 1, "title": "Sách 1", "author": "Tác giả A", "available": True, "updated_at": datetime.utcnow().isoformat()},
    {"id": 2, "title": "Sách 2", "author": "Tác giả B", "available": True, "updated_at": datetime.utcnow().isoformat()},
    {"id": 3, "title": "Sách 3", "author": "Tác giả C", "available": True, "updated_at": datetime.utcnow().isoformat()},
    {"id": 4, "title": "Sách 4", "author": "Tác giả D", "available": True, "updated_at": datetime.utcnow().isoformat()},
    {"id": 5, "title": "Sách 5", "author": "Tác giả E", "available": True, "updated_at": datetime.utcnow().isoformat()},
    {"id": 6, "title": "Sách 6", "author": "Tác giả F", "available": True, "updated_at": datetime.utcnow().isoformat()},
    {"id": 7, "title": "Sách 7", "author": "Tác giả G", "available": True, "updated_at": datetime.utcnow().isoformat()},
    {"id": 8, "title": "Sách 8", "author": "Tác giả H", "available": True, "updated_at": datetime.utcnow().isoformat()},
    {"id": 9, "title": "Sách 9", "author": "Tác giả I", "available": True, "updated_at": datetime.utcnow().isoformat()},
    {"id": 10, "title": "Sách 10", "author": "Tác giả J", "available": True, "updated_at": datetime.utcnow().isoformat()},
    {"id": 11, "title": "Sách 11", "author": "Tác giả K", "available": True, "updated_at": datetime.utcnow().isoformat()},
    {"id": 12, "title": "Sách 12", "author": "Tác giả L", "available": True, "updated_at": datetime.utcnow().isoformat()},
]

loans = []

def get_all_books(page=1, per_page=10):
    start = (page - 1) * per_page
    end = start + per_page
    paginated_books = books[start:end]
    return paginated_books, len(books)

def find_book_by_id(book_id):
    return next((b for b in books if b["id"] == book_id), None)

def _touch(book):
    book['updated_at'] = datetime.utcnow().isoformat()

def borrow_book(book_id, borrower_id=None):
    book = find_book_by_id(book_id)
    if book and book["available"]:
        book["available"] = False
        _touch(book)
        loans.append({
            'book_id': book_id,
            'borrower_id': borrower_id,
            'borrowed_at': datetime.utcnow().isoformat(),
            'returned_at': None
        })
        return True
    return False

def return_book(book_id):
    book = find_book_by_id(book_id)
    if book and not book["available"]:
        book["available"] = True
        _touch(book)
        for ln in reversed(loans):
            if ln['book_id'] == book_id and ln['returned_at'] is None:
                ln['returned_at'] = datetime.utcnow().isoformat()
                break
        return True
    return False

def get_books_snapshot():
    """
    Trả về snapshot dùng để tính ETag toàn cục danh sách:
    - version: tăng khi có thay đổi available/updated_at
    - count: số lượng sách
    """
    version = "|".join(f"{b['id']}:{int(not b['available'])}:{b['updated_at']}" for b in books)
    return {'version': version, 'count': len(books)}


