from __future__ import annotations
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config.update(
    SQLALCHEMY_DATABASE_URI="sqlite:///library.db",
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    SECRET_KEY="dev-secret-key"  # cho flash message
)

db = SQLAlchemy(app)

# ------------------
# MODELS
# ------------------
class Book(db.Model):
    __tablename__ = "books"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    author = db.Column(db.String(255), nullable=False)
    isbn = db.Column(db.String(32))
    copies_total = db.Column(db.Integer, nullable=False, default=1)
    copies_available = db.Column(db.Integer, nullable=False, default=1)

    def can_borrow(self) -> bool:
        return self.copies_available > 0


class Loan(db.Model):
    __tablename__ = "loans"
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey("books.id"), nullable=False)
    borrower = db.Column(db.String(255), nullable=False)
    borrowed_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    due_at = db.Column(db.DateTime, nullable=False)
    returned_at = db.Column(db.DateTime)

    book = db.relationship("Book", backref=db.backref("loans", lazy=True))

    @property
    def is_active(self) -> bool:
        return self.returned_at is None

    @property
    def is_overdue(self) -> bool:
        return self.is_active and datetime.utcnow() > self.due_at


with app.app_context():
    db.create_all()

# ------------------
# ROUTES (UI)
# ------------------
@app.route("/")
def dashboard():
    total_books = db.session.scalar(db.select(db.func.count(Book.id))) or 0
    available = db.session.scalar(db.select(db.func.sum(Book.copies_available))) or 0
    active_loans = db.session.scalar(db.select(db.func.count(Loan.id)).where(Loan.returned_at.is_(None))) or 0
    overdue_loans = db.session.scalar(db.select(db.func.count(Loan.id)).where(Loan.returned_at.is_(None), Loan.due_at < datetime.utcnow())) or 0
    return render_template("dashboard.html", stats=dict(total_books=total_books, available=available, active_loans=active_loans, overdue_loans=overdue_loans))

# ---- Books CRUD ----
@app.route("/books")
def books():
    items = Book.query.order_by(Book.id.desc()).all()
    return render_template("books.html", books=items)

@app.route("/books/add", methods=["GET", "POST"])
def add_book():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        author = request.form.get("author", "").strip()
        isbn = request.form.get("isbn", "").strip() or None
        total = max(1, int(request.form.get("copies_total", 1)))
        book = Book(title=title, author=author, isbn=isbn, copies_total=total, copies_available=total)
        db.session.add(book)
        db.session.commit()
        flash("Đã thêm sách.")
        return redirect(url_for("books"))
    return render_template("book_form.html", book=None)

@app.route("/books/<int:book_id>/edit", methods=["GET", "POST"])
def edit_book(book_id: int):
    book = Book.query.get_or_404(book_id)
    if request.method == "POST":
        book.title = request.form.get("title", book.title).strip()
        book.author = request.form.get("author", book.author).strip()
        book.isbn = request.form.get("isbn", "").strip() or None
        new_total = max(1, int(request.form.get("copies_total", book.copies_total)))
        delta = new_total - book.copies_total
        book.copies_total = new_total
        book.copies_available = max(0, book.copies_available + delta)
        db.session.commit()
        flash("Đã cập nhật sách.")
        return redirect(url_for("books"))
    return render_template("book_form.html", book=book)

@app.route("/books/<int:book_id>/delete")
def delete_book(book_id: int):
    book = Book.query.get_or_404(book_id)
    # chặn xoá khi còn loan active cho sách này
    active = Loan.query.filter_by(book_id=book.id, returned_at=None).count()
    if active:
        flash("Không thể xoá: Sách đang có lượt mượn chưa trả.")
        return redirect(url_for("books"))
    db.session.delete(book)
    db.session.commit()
    flash("Đã xoá sách.")
    return redirect(url_for("books"))

# ---- Borrow / Return ----
@app.route("/loans")
def loans():
    books = Book.query.order_by(Book.title.asc()).all()
    active_loans = Loan.query.filter_by(returned_at=None).order_by(Loan.borrowed_at.desc()).all()
    history = Loan.query.filter(Loan.returned_at.isnot(None)).order_by(Loan.returned_at.desc()).limit(50).all()
    return render_template("loans.html", books=books, active_loans=active_loans, history=history)

@app.route("/borrow", methods=["POST"])
def borrow():
    book_id = int(request.form.get("book_id"))
    borrower = request.form.get("borrower", "").strip()
    days = max(1, int(request.form.get("days", 7)))

    book = Book.query.get_or_404(book_id)
    if not borrower:
        flash("Vui lòng nhập tên người mượn.")
        return redirect(url_for("loans"))
    if not book.can_borrow():
        flash("Sách này đã hết bản có sẵn.")
        return redirect(url_for("loans"))

    loan = Loan(book_id=book.id, borrower=borrower, due_at=datetime.utcnow() + timedelta(days=days))
    db.session.add(loan)
    book.copies_available -= 1
    db.session.commit()
    flash("Đã mượn sách.")
    return redirect(url_for("loans"))

@app.route("/return/<int:loan_id>", methods=["POST"])
def return_book(loan_id: int):
    loan = Loan.query.get_or_404(loan_id)
    if loan.returned_at is not None:
        flash("Lượt mượn này đã trả trước đó.")
        return redirect(url_for("loans"))
    loan.returned_at = datetime.utcnow()
    loan.book.copies_available = min(loan.book.copies_total, loan.book.copies_available + 1)
    db.session.commit()
    flash("Đã trả sách.")
    return redirect(url_for("loans"))

if __name__ == "__main__":
    app.run(debug=True)