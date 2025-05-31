# Remove local db definition, import from app
# from flask_sqlalchemy import SQLAlchemy 
from flask_login import UserMixin # Keep UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# Import the shared db instance from app.py
from app import db, login_manager # Import db and login_manager

# The user_loader should be defined in app.py where login_manager is initialized
# @login_manager.user_loader
# def load_user(user_id):
#     return User.query.get(int(user_id))

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    orders = db.relationship("Order", backref="customer", lazy="dynamic")
    cart = db.relationship("Cart", backref="customer", uselist=False) # One-to-one relationship

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.username}>"

class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(256))
    category = db.Column(db.String(64)) # e.g., currency, item, pass
    game_type = db.Column(db.String(64), index=True) # e.g., pubg, free_fire
    region = db.Column(db.String(64)) # e.g., global, NA, EU
    stock = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    order_items = db.relationship("OrderItem", backref="game", lazy="dynamic")
    cart_items = db.relationship("CartItem", backref="game", lazy="dynamic")

    def __repr__(self):
        return f"<Game {self.name}>"

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    status = db.Column(db.String(64), default="pending") # e.g., pending, processing, completed, cancelled
    total_amount = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    items = db.relationship("OrderItem", backref="order", lazy="dynamic", cascade="all, delete-orphan")
    payment = db.relationship("Payment", backref="order", uselist=False, cascade="all, delete-orphan") # One-to-one

    def __repr__(self):
        return f"<Order {self.id}>"

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("order.id"), nullable=False)
    game_id = db.Column(db.Integer, db.ForeignKey("game.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False) # Price at the time of order
    status = db.Column(db.String(64), default="pending") # e.g., pending, fulfilled, failed
    code = db.Column(db.String(256), nullable=True) # Digital code if applicable
    game_account_id = db.Column(db.String(128), nullable=True) # Game account ID for direct credit

    def __repr__(self):
        return f"<OrderItem {self.id} for Order {self.order_id}>"

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("order.id"), nullable=False)
    payment_method = db.Column(db.String(64)) # e.g., credit_card, paypal
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(64), default="pending") # e.g., pending, completed, failed
    transaction_id = db.Column(db.String(128), nullable=True) # From payment gateway
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Payment {self.id} for Order {self.order_id}>"

class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    items = db.relationship("CartItem", backref="cart", lazy="dynamic", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Cart {self.id} for User {self.user_id}>"

class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cart_id = db.Column(db.Integer, db.ForeignKey("cart.id"), nullable=False)
    game_id = db.Column(db.Integer, db.ForeignKey("game.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    game_account_id = db.Column(db.String(128), nullable=True) # Optional game account ID for pre-filling checkout

    def __repr__(self):
        return f"<CartItem {self.id} for Cart {self.cart_id}>"

