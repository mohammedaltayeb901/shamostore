import unittest
import os
from datetime import datetime
from app import create_app, db
# Explicitly import all models needed for testing *before* test classes
from models import User, Game, Order, OrderItem, Payment, Cart, CartItem 
from config import Config
from shipping import GameShippingService

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:" # Use in-memory SQLite for tests
    WTF_CSRF_ENABLED = False # Disable CSRF for testing forms
    SECRET_KEY = "test-secret-key"

class UserModelCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all() # Ensure tables are created

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_password_hashing(self):
        u = User(username="susan", email="susan@example.com")
        u.set_password("cat")
        self.assertFalse(u.check_password("dog"))
        self.assertTrue(u.check_password("cat"))

    def test_user_creation(self):
        u = User(username="john", email="john@example.com", is_admin=True)
        db.session.add(u)
        db.session.commit()
        user = User.query.filter_by(email="john@example.com").first()
        self.assertIsNotNone(user)
        self.assertEqual(user.username, "john")
        self.assertTrue(user.is_admin)

class GameModelCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all() # Ensure tables are created

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_game_creation(self):
        g = Game(name="Test Game", price=10.99, game_type="test", category="Action", stock=100, is_active=True)
        db.session.add(g)
        db.session.commit()
        game = Game.query.filter_by(name="Test Game").first()
        self.assertIsNotNone(game)
        self.assertEqual(game.price, 10.99)
        self.assertEqual(game.stock, 100)
        self.assertTrue(game.is_active)

class ShippingServiceCase(unittest.TestCase):
    # No DB interaction needed here, so no setUp/tearDown required
    def test_code_generation(self):
        code1 = GameShippingService.generate_digital_code("pubg")
        code2 = GameShippingService.generate_digital_code("freefire")
        self.assertTrue(code1.startswith("PUBG-"))
        self.assertTrue(code2.startswith("FREE-"))
        self.assertNotEqual(code1, code2)
        # Check the format of the last part (4 characters)
        self.assertEqual(len(code1.split("-")[-1]), 4) # Last part should be 4 chars

class IntegrationTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all() # Ensure tables are created
        self.client = self.app.test_client()
        # Create a test user
        u = User(username="testuser", email="test@example.com")
        u.set_password("password")
        db.session.add(u)
        # Create a test game
        g = Game(name="Integration Test Game", price=5.00, game_type="test", category="Test", stock=10)
        db.session.add(g)
        db.session.commit()
        self.test_user = u
        self.test_game = g

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_home_page(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("متجر الألعاب".encode('utf-8'), response.data) # "متجر الألعاب"

    def test_registration_and_login(self):
        # Test registration
        response = self.client.post("/auth/register", data={
            "username": "newuser",
            "email": "new@example.com",
            "password": "newpassword",
            "confirm_password": "newpassword"
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("تسجيل الدخول".encode('utf-8'), response.data) # "تسجيل الدخول"
        user = User.query.filter_by(email="new@example.com").first()
        self.assertIsNotNone(user)

        # Test login
        response = self.client.post("/auth/login", data={
            "email": "new@example.com",
            "password": "newpassword"
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("متجر الألعاب".encode('utf-8'), response.data) # "متجر الألعاب"
        self.assertIn("تسجيل الخروج".encode('utf-8'), response.data) # "تسجيل الخروج"

    def test_add_to_cart_api(self):
        # Login first
        self.client.post("/auth/login", data={
            "email": "test@example.com",
            "password": "password"
        }, follow_redirects=True)
        
        # Add game to cart via API
        response = self.client.post("/api/cart/add", json={
            "game_id": self.test_game.id,
            "quantity": 1
        })
        self.assertEqual(response.status_code, 200)
        json_response = response.get_json()
        self.assertTrue(json_response["success"])
        self.assertIn("تمت إضافة المنتج إلى السلة بنجاح", json_response["message"])

        # Check cart via API
        response = self.client.get("/api/cart")
        self.assertEqual(response.status_code, 200)
        json_response = response.get_json()
        self.assertTrue(json_response["success"])
        # Ensure data and items exist in response
        self.assertIn("data", json_response)
        self.assertIsNotNone(json_response["data"])
        self.assertIn("items", json_response["data"])
        self.assertIsNotNone(json_response["data"]["items"])
        # Now check the items
        self.assertEqual(len(json_response["data"]["items"]), 1)
        self.assertEqual(json_response["data"]["items"][0]["game_id"], self.test_game.id)
        self.assertEqual(json_response["data"]["total"], 5.00)

    def test_checkout_process(self):
        # Login
        self.client.post("/auth/login", data={
            "email": "test@example.com",
            "password": "password"
        }, follow_redirects=True)
        
        # Add item to cart
        self.client.post("/api/cart/add", json={"game_id": self.test_game.id, "quantity": 1})

        # Perform checkout via API (simulated)
        response = self.client.post("/api/checkout", json={"payment_method": "simulated_credit_card"})
        self.assertEqual(response.status_code, 200)
        json_response = response.get_json()
        self.assertTrue(json_response["success"])
        self.assertIn("order_id", json_response)
        order_id = json_response["order_id"]

        # Verify order exists
        order = Order.query.get(order_id)
        self.assertIsNotNone(order)
        self.assertEqual(order.user_id, self.test_user.id)  # Changed from customer_id to user_id to match model
        self.assertEqual(order.total_amount, 5.00)
        self.assertEqual(order.status, "completed") # Status after fulfillment (changed from pending as fulfillment happens immediately)
        
        # Check order items
        items = OrderItem.query.filter_by(order_id=order_id).all()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].game_id, self.test_game.id)
        
        # Check payment
        payment = Payment.query.filter_by(order_id=order_id).first()
        self.assertIsNotNone(payment)
        self.assertEqual(payment.status, "completed") # Payment marked completed in simulation

    # Add more tests for admin functions, order fulfillment, etc.

if __name__ == "__main__":
    unittest.main(verbosity=2)
