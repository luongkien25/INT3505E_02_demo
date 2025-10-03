from flask import jsonify, request, abort

@app.route("/api/books", methods=["GET", "POST"])
def books_api():
    if request.method == "GET":
        items = Book.query.order_by(Book.id.desc()).all()
        return jsonify([{
            "id": b.id, "title": b.title, "author": b.author,
            "isbn": b.isbn, "copies_total": b.copies_total,
            "copies_available": b.copies_available
        }])
    data = request.get_json(force=True, silent=True) or {}
    title = (data.get("title") or "").strip()
    author = (data.get("author") or "").strip()
    if not title or not author:
        abort(400, description="title and author are required")
    total = max(1, int(data.get("copies_total") or 1))
    book = Book(title=title, author=author, isbn=data.get("isbn"), copies_total=total,
                copies_available=total)
    db.session.add(book); db.session.commit()
    resp = jsonify({"id": book.id})
    resp.status_code = 201
    resp.headers["Location"] = url_for("book_api", book_id=book.id)
    return resp

@app.route("/api/books/<int:book_id>", methods=["GET", "PUT", "PATCH", "DELETE"])
def book_api(book_id):
    book = Book.query.get_or_404(book_id)
    if request.method == "GET":
        return jsonify({"id": book.id, "title": book.title, ...})
    if request.method in ("PUT","PATCH"):
        data = request.get_json(force=True, silent=True) or {}
        ...
        db.session.commit()
        return jsonify({"id": book.id})
    active = Loan.query.filter_by(book_id=book.id, returned_at=None).count()
    if active:
        abort(409, description="Book has active loans")
    db.session.delete(book); db.session.commit()
    return ("", 204)

@app.route("/api/loans", methods=["POST"])
def create_loan():
    data = request.get_json(force=True, silent=True) or {}
    book = Book.query.get_or_404(int(data.get("book_id", 0)))
    if not book.can_borrow(): abort(422, description="No copies available")
    borrower = (data.get("borrower") or "").strip()
    if not borrower: abort(400, description="borrower required")
    days = max(1, int(data.get("days") or 7))
    loan = Loan(book_id=book.id, borrower=borrower,
                due_at=datetime.utcnow() + timedelta(days=days))
    db.session.add(loan); book.copies_available -= 1; db.session.commit()
    return jsonify({"id": loan.id}), 201

@app.route("/api/loans/<int:loan_id>", methods=["PATCH"])
def return_loan(loan_id):
    loan = Loan.query.get_or_404(loan_id)
    data = request.get_json(force=True, silent=True) or {}
    if data.get("returned_at", True):  
        if loan.returned_at: abort(409, description="Loan already returned")
        loan.returned_at = datetime.utcnow()
        loan.book.copies_available = min(loan.book.copies_total, loan.book.copies_available + 1)
        db.session.commit()
    return ("", 204)
