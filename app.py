from flask import Flask, render_template, request, redirect, url_for, flash, session
from models import db, User, Product, Order, OrderItem
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///shop.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Initialize shopping cart in session
def init_cart():
    if 'cart' not in session:
        session['cart'] = {}

@app.route('/')
def home():
    products = Product.query.all()
    init_cart()
    return render_template('index.html', products=products)

@app.route('/add_to_cart/<int:product_id>')
@login_required
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)
    
    # Initialize cart if not exists
    if 'cart' not in session:
        session['cart'] = {}
    
    # Add product to cart
    cart = session['cart']
    if str(product_id) in cart:
        cart[str(product_id)] += 1
    else:
        cart[str(product_id)] = 1
    
    session['cart'] = cart
    flash(f'Added {product.name} to cart!')
    return redirect(url_for('home'))

@app.route('/cart')
@login_required
def cart():
    cart_items = []
    total = 0
    
    if 'cart' in session:
        for product_id, quantity in session['cart'].items():
            product = Product.query.get(product_id)
            if product:
                item_total = product.price * quantity
                cart_items.append({
                    'product': product,
                    'quantity': quantity,
                    'total': item_total
                })
                total += item_total
    
    return render_template('cart.html', cart_items=cart_items, total=total)

@app.route('/checkout')
@login_required
def checkout():
    cart = session.get('cart', {})
    if not cart:
        flash('Your cart is empty!')
        return redirect(url_for('home'))
    
    total = 0
    for product_id, quantity in cart.items():
        product = Product.query.get(product_id)
        if product:
            total += product.price * quantity
    
    # Create order
    order = Order(user_id=current_user.id, total_amount=total)
    db.session.add(order)
    db.session.flush()  # Get order ID without committing
    
    # Create order items
    for product_id, quantity in cart.items():
        product = Product.query.get(product_id)
        if product:
            # Update stock
            product.stock -= quantity
            
            order_item = OrderItem(
                order_id=order.id,
                product_id=product_id,
                quantity=quantity,
                price=product.price
            )
            db.session.add(order_item)
    
    db.session.commit()
    
    # Clear cart
    session['cart'] = {}
    
    flash(f'Order placed successfully! Total: ${total:.2f}')
    return redirect(url_for('home'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        # Check if user already exists
        if User.query.filter_by(username=username).first() or User.query.filter_by(email=email).first():
            flash('Username or email already exists')
            return redirect(url_for('register'))
        
        # Create new user
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.pop('cart', None)  # Clear cart on logout
    return redirect(url_for('home'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        # Add some sample products if none exist
        if Product.query.count() == 0:
            sample_products = [
                Product(name='Laptop', description='High-performance laptop', price=999.99, stock=10),
                Product(name='Smartphone', description='Latest smartphone model', price=699.99, stock=20),
                Product(name='Headphones', description='Wireless noise-cancelling headphones', price=199.99, stock=30)
            ]
            for product in sample_products:
                db.session.add(product)
            db.session.commit()
            
    app.run(debug=True)