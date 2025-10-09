from flask import Flask, jsonify, request

app = Flask(__name__)

books = [
    {"id": 1, "title": "Sách 1", "author": "Tác giả A", "available": True},
    {"id": 2, "title": "Sách 2", "author": "Tác giả B", "available": True},
    {"id": 3, "title": "Sách 3", "author": "Tác giả C", "available": True}
]

@app.route('/api/books', methods=['GET'])
def get_books():
    return jsonify(books)

@app.route('/api/borrow/<int:book_id>', methods=['POST'])
def borrow_book(book_id):
    book = next((b for b in books if b["id"] == book_id), None)
    if book and book["available"]:
        book["available"] = False
        return jsonify({"message": f"Sách '{book['title']}' đã được mượn thành công!"}), 200
    elif book:
        return jsonify({"message": f"Sách '{book['title']}' hiện không có sẵn!"}), 400
    return jsonify({"message": "Sách không tồn tại!"}), 404

@app.route('/api/return/<int:book_id>', methods=['POST'])
def return_book(book_id):
    book = next((b for b in books if b["id"] == book_id), None)
    if book and not book["available"]:
        book["available"] = True
        return jsonify({"message": f"Sách '{book['title']}' đã được trả thành công!"}), 200
    elif book:
        return jsonify({"message": f"Sách '{book['title']}' chưa được mượn!"}), 400
    return jsonify({"message": "Sách không tồn tại!"}), 404

if __name__ == '__main__':
    app.run(debug=True)
