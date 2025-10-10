from books import get_all_books, borrow_book, return_book, find_book_by_id

def get_books_service(page=1, per_page=10):
    paginated_books, total_books = get_all_books(page, per_page)
    return paginated_books, total_books

def can_borrow(book_id):
    book = find_book_by_id(book_id)
    if book and book['available']:
        return True
    return False

def borrow_book_service(book_id):
    if can_borrow(book_id):
        return borrow_book(book_id)
    return None

def can_return(book_id):
    book = find_book_by_id(book_id)
    if book and not book['available']: 
        return True
    return False

def return_book_service(book_id):
    if can_return(book_id):
        return return_book(book_id)
    return None

def code_on_demand_service():
    return """
    <script>
        alert('Hello from server!');
    </script>
    """
