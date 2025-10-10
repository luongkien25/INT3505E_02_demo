# Dữ liệu sách (thông tin giả lập)
books = [
    {"id": 1, "title": "Sách 1", "author": "Tác giả A", "available": True},
    {"id": 2, "title": "Sách 2", "author": "Tác giả B", "available": True},
    {"id": 3, "title": "Sách 3", "author": "Tác giả C", "available": True}
]

def get_all_books():
    return books

def find_book_by_id(book_id):
    return next((b for b in books if b["id"] == book_id), None)

def borrow_book(book_id):
    book = find_book_by_id(book_id)
    if book and book["available"]:
        book["available"] = False  
        return book
    return None

def return_book(book_id):
    book = find_book_by_id(book_id)
    if book and not book["available"]:
        book["available"] = True  
        return book
    return None
