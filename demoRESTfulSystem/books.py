# Tệp books.py

# Dữ liệu sách
books = [
    {"id": 1, "title": "Sách 1", "author": "Tác giả A", "available": True},
    {"id": 2, "title": "Sách 2", "author": "Tác giả B", "available": True},
    {"id": 3, "title": "Sách 3", "author": "Tác giả C", "available": True},
    {"id": 4, "title": "Sách 4", "author": "Tác giả D", "available": True},
    {"id": 5, "title": "Sách 5", "author": "Tác giả E", "available": True},
    {"id": 6, "title": "Sách 6", "author": "Tác giả F", "available": True},
    {"id": 7, "title": "Sách 7", "author": "Tác giả G", "available": True},
    {"id": 8, "title": "Sách 8", "author": "Tác giả H", "available": True},
    {"id": 9, "title": "Sách 9", "author": "Tác giả I", "available": True},
    {"id": 10, "title": "Sách 10", "author": "Tác giả J", "available": True},
    {"id": 11, "title": "Sách 11", "author": "Tác giả K", "available": True},
    {"id": 12, "title": "Sách 12", "author": "Tác giả L", "available": True}
]

def get_all_books(page=1, per_page=10):
    start = (page - 1) * per_page
    end = start + per_page
    paginated_books = books[start:end]
    return paginated_books, len(books) 

def find_book_by_id(book_id):
    return next((b for b in books if b["id"] == book_id), None)

def borrow_book(book_id):
    book = find_book_by_id(book_id)
    if book and book["available"]:
        book["available"] = False  
    return None


def return_book(book_id):
    book = find_book_by_id(book_id)
    if book and not book["available"]:
        book["available"] = True 
        return book
    return None

