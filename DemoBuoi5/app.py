import os
from datetime import datetime, timedelta
from flask import Flask, jsonify, request, url_for, g
from extensions import db
from models import Product, Customer, Order, Role
from auth import auth_bp, auth_required, init_authlib

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///shop.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['JWT_SECRET'] = os.environ.get('JWT_SECRET', 'change-me-in-prod')
app.config['JWT_ALG'] = 'HS256'
app.config['ACCESS_TOKEN_EXPIRES'] = timedelta(minutes=15)   
app.config['REFRESH_TOKEN_EXPIRES'] = timedelta(days=7)    

app.config['OAUTH_GOOGLE_CLIENT_ID'] = os.environ.get('GOOGLE_CLIENT_ID') or ''
app.config['OAUTH_GOOGLE_CLIENT_SECRET'] = os.environ.get('GOOGLE_CLIENT_SECRET') or ''

db.init_app(app)

def product_to_dict(p):
    return {'id': p.id, 'name': p.name, 'price': p.price}

def customer_to_dict(c):
    return {'id': c.id, 'name': c.name, 'email': c.email, 'roles': [r.name for r in c.roles]}

def order_to_dict(o):
    return {
        'id': o.id,
        'customer_id': o.customer_id,
        'product_id': o.product_id,
        'order_date': o.order_date.isoformat() if o.order_date else None
    }

with app.app_context():
    db.create_all()
    if not Role.query.filter_by(name='admin').first():
        db.session.add(Role(name='admin'))
    if not Role.query.filter_by(name='user').first():
        db.session.add(Role(name='user'))
    db.session.commit()
    if not Customer.query.filter_by(email='admin@example.com').first():
        admin = Customer(name='Admin', email='admin@example.com')
        admin.set_password('Admin@123')  
        admin.roles = [Role.query.filter_by(name='admin').first()]
        db.session.add(admin)
        db.session.commit()

init_authlib(app)
app.register_blueprint(auth_bp)

@app.route('/')
def index():
    return jsonify({'message': 'API is running', 'auth': {
        'register': '/auth/register', 'login': '/auth/login',
        'refresh': '/auth/refresh', 'me': '/auth/me',
        'google_login': '/auth/google'
    }})

@app.route('/products', methods=['POST'])
@auth_required(scopes=['product:write'], roles=['admin'])
def add_product():
    data = request.get_json() or {}
    if 'name' not in data or 'price' not in data:
        return jsonify({'message': 'Missing required fields: name, price'}), 400
    new_product = Product(name=data['name'], price=data['price'])
    db.session.add(new_product)
    db.session.commit()
    return jsonify(product_to_dict(new_product)), 201

@app.route('/products', methods=['GET'])
@auth_required(scopes=['product:read'])
def list_products():
    page = request.args.get('page', type=int)
    per_page = request.args.get('per_page', 10, type=int)
    limit = request.args.get('limit', type=int)
    offset = request.args.get('offset', type=int)

    if page is not None:
        pag = Product.query.paginate(page=page, per_page=per_page, error_out=False)
        items = [product_to_dict(p) for p in pag.items]
        return jsonify({
            'items': items,
            'meta': {'total': pag.total, 'page': pag.page, 'per_page': pag.per_page, 'pages': pag.pages},
            'links': {
                'self': url_for('list_products', page=pag.page, per_page=pag.per_page, _external=True),
                'next': url_for('list_products', page=pag.next_num, per_page=pag.per_page, _external=True) if pag.has_next else None,
                'prev': url_for('list_products', page=pag.prev_num, per_page=pag.per_page, _external=True) if pag.has_prev else None,
            }
        })

    q = Product.query
    if offset is not None:
        q = q.offset(offset)
    if limit is not None:
        q = q.limit(limit)
    products = q.all()
    return jsonify([product_to_dict(p) for p in products])

@app.route('/customers', methods=['POST'])
@auth_required(scopes=['customer:write'], roles=['admin'])
def add_customer():
    data = request.get_json() or {}
    if 'name' not in data or 'email' not in data or 'password' not in data:
        return jsonify({'message': 'Missing required fields: name, email, password'}), 400
    if Customer.query.filter_by(email=data['email']).first():
        return jsonify({'message': 'Email already exists'}), 409
    new_customer = Customer(name=data['name'], email=data['email'])
    new_customer.set_password(data['password'])
    role_user = Role.query.filter_by(name='user').first()
    new_customer.roles = [role_user]
    db.session.add(new_customer)
    db.session.commit()
    return jsonify(customer_to_dict(new_customer)), 201

@app.route('/customers', methods=['GET'])
@auth_required(scopes=['customer:read'], roles=['admin'])
def list_customers():
    customers = Customer.query.all()
    return jsonify([customer_to_dict(c) for c in customers])

@app.route('/customers/<int:customer_id>/orders', methods=['GET'])
@auth_required(scopes=['order:read'], allow_self=True, customer_id_param='customer_id')
def list_orders_by_customer(customer_id):
    page = request.args.get('page', type=int)
    per_page = request.args.get('per_page', 10, type=int)
    q = Order.query.filter_by(customer_id=customer_id).order_by(Order.order_date.desc())
    if page is not None:
        pag = q.paginate(page=page, per_page=per_page, error_out=False)
        return jsonify({
            'items': [order_to_dict(o) for o in pag.items],
            'meta': {'total': pag.total, 'page': pag.page, 'per_page': pag.per_page, 'pages': pag.pages}
        })
    return jsonify([order_to_dict(o) for o in q.all()])

@app.route('/orders', methods=['POST'])
@auth_required(scopes=['order:write'])
def add_order():
    data = request.get_json() or {}
    if 'customer_id' not in data or 'product_id' not in data or 'order_date' not in data:
        return jsonify({'message': 'Missing required fields: customer_id, product_id, order_date'}), 400
    try:
        order_date = datetime.fromisoformat(data['order_date'])
    except Exception:
        return jsonify({'message': 'order_date must be ISO format YYYY-MM-DDTHH:MM:SS'}), 400
    if not Customer.query.get(data['customer_id']):
        return jsonify({'message': 'Customer not found'}), 404
    if not Product.query.get(data['product_id']):
        return jsonify({'message': 'Product not found'}), 404

    if 'admin' not in getattr(g, 'current_roles', set()) and int(data['customer_id']) != getattr(g, 'current_user_id', -1):
        return jsonify({'message': 'Forbidden: you can only create your own order'}), 403

    new_order = Order(customer_id=data['customer_id'], product_id=data['product_id'], order_date=order_date)
    db.session.add(new_order)
    db.session.commit()
    return jsonify(order_to_dict(new_order)), 201

@app.route('/orders', methods=['GET'])
@auth_required(scopes=['order:read'], roles=['admin'])
def list_orders():
    page = request.args.get('page', type=int)
    per_page = request.args.get('per_page', 10, type=int)
    q = Order.query.order_by(Order.order_date.desc())
    if page is not None:
        pag = q.paginate(page=page, per_page=per_page, error_out=False)
        return jsonify({
            'items': [order_to_dict(o) for o in pag.items],
            'meta': {'total': pag.total, 'page': pag.page, 'per_page': pag.per_page, 'pages': pag.pages}
        })
    return jsonify([order_to_dict(o) for o in q.all()])

@app.route('/favicon.ico')
def favicon():
    return ('', 204)

if __name__ == '__main__':
    app.run(debug=True)

