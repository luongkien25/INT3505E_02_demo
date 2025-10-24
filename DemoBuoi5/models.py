from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db

class Product(db.Model):
    __tablename__ = 'product'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    def __repr__(self):
        return f"<Product {self.name}>"

class Role(db.Model):
    __tablename__ = 'role'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    def __repr__(self):
        return f"<Role {self.name}>"

customer_roles = db.Table(
    'customer_roles',
    db.Column('customer_id', db.Integer, db.ForeignKey('customer.id'), primary_key=True),
    db.Column('role_id', db.Integer, db.ForeignKey('role.id'), primary_key=True)
)

class Customer(db.Model):
    __tablename__ = 'customer'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False, default='')

    roles = db.relationship('Role', secondary=customer_roles, lazy='joined', backref='customers')

    def set_password(self, raw_password: str):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password_hash, raw_password)

    def __repr__(self):
        return f"<Customer {self.name}>"

class Order(db.Model):
    __tablename__ = 'order'
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    order_date = db.Column(db.DateTime, nullable=False)

    customer = db.relationship('Customer', backref='orders')
    product = db.relationship('Product', backref='orders')

    def __repr__(self):
        return f"<Order {self.id}>"

class RefreshToken(db.Model):
    __tablename__ = 'refresh_token'
    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(36), nullable=False, unique=True)  # JWT ID
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    revoked = db.Column(db.Boolean, default=False, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    customer = db.relationship('Customer', backref='refresh_tokens')

    def __repr__(self):
        return f"<RefreshToken {self.jti} revoked={self.revoked}>"


