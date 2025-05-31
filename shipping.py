import random
import string
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from models import OrderItem, Order, User, db, Game # Import Game
from flask import current_app, render_template

class GameShippingService:
    """Service for handling game shipping functionality"""
    
    @staticmethod
    def generate_digital_code(game_type, length=16):
        """Generate a random digital code for game items"""
        prefix = "CODE-"
        if game_type:
            prefix = game_type.upper()[:4] + "-"
        
        chars = string.ascii_uppercase + string.digits
        code_part = "".join(random.choice(chars) for _ in range(length))
        # Ensure 4 groups of 4 characters
        formatted_code = f"{code_part[:4]}-{code_part[4:8]}-{code_part[8:12]}-{code_part[12:16]}"
        timestamp = datetime.now().strftime("%y%m%d%H%M") # Add time for more uniqueness
        return f"{prefix}{timestamp}-{formatted_code}"
    
    @staticmethod
    def send_order_confirmation_email(order_id):
        """Send order confirmation email to customer (Simulated)"""
        order = Order.query.get(order_id)
        if not order or not order.customer:
            print(f"Error: Order {order_id} or customer not found for email.")
            return False, "Order or customer not found"
        
        user = order.customer
        subject = f"تأكيد الطلب وشحن الأكواد - الطلب #{order.id}"
        sender = current_app.config.get("MAIL_DEFAULT_SENDER", "noreply@example.com")
        recipient = user.email

        # Build email content with codes
        email_body = f"<h1>شكراً لطلبك #{order.id}!</h1>"
        email_body += "<p>لقد تم شحن طلبك بنجاح. إليك تفاصيل المنتجات والأكواد الرقمية:</p>"
        email_body += "<ul>"
        for item in order.items:
            email_body += f"<li><strong>{item.game.name}</strong> (الكمية: {item.quantity})"
            if item.code:
                email_body += f" - الكود: <code>{item.code}</code>"
            elif item.game_account_id:
                 email_body += f" - تم الشحن إلى معرف اللاعب: {item.game_account_id}"
            else:
                 email_body += " - (لا يتطلب كود)"
            email_body += "</li>"
        email_body += "</ul>"
        email_body += "<p>يمكنك أيضاً مراجعة تفاصيل طلبك في حسابك على موقعنا.</p>"

        # Simulate sending
        print(f"--- محاكاة إرسال بريد إلكتروني ---")
        print(f"إلى: {recipient}")
        print(f"من: {sender}")
        print(f"الموضوع: {subject}")
        print(f"المحتوى (HTML):\n{email_body}")
        # In a real app, use smtplib or a mail service library here
        # Example using smtplib (requires mail server config):
        # try:
        #     msg = MIMEMultipart("alternative")
        #     msg["Subject"] = subject
        #     msg["From"] = sender
        #     msg["To"] = recipient
        #     msg.attach(MIMEText(email_body, "html"))
        #     with smtplib.SMTP(current_app.config["MAIL_SERVER"], current_app.config["MAIL_PORT"]) as server:
        #         if current_app.config["MAIL_USE_TLS"]:
        #             server.starttls()
        #         if current_app.config["MAIL_USERNAME"] and current_app.config["MAIL_PASSWORD"]:
        #             server.login(current_app.config["MAIL_USERNAME"], current_app.config["MAIL_PASSWORD"])
        #         server.sendmail(sender, recipient, msg.as_string())
        #     print("Email sent successfully (simulated).")
        # except Exception as e:
        #     print(f"Email sending failed: {e}")
        #     return False, f"Email sending failed: {e}"
        print(f"--- نهاية محاكاة البريد الإلكتروني ---")
        
        return True, "Email simulation complete"

    @staticmethod
    def fulfill_order(order_id):
        """Process order fulfillment"""
        order = Order.query.get(order_id)
        if not order:
            print(f"Fulfillment Error: Order {order_id} not found.")
            return False, "Order not found"

        # Ensure payment is completed before fulfillment (important in real app)
        # if not order.payment or order.payment.status != "completed":
        #     print(f"Fulfillment Error: Payment for order {order_id} not completed.")
        #     return False, "Payment not completed"

        if order.status not in ["pending", "processing", "failed_fulfillment"]: # Allow re-fulfillment attempt
             print(f"Fulfillment Info: Order {order_id} status is {order.status}, skipping fulfillment.")
             return True, f"Order status is {order.status}, fulfillment skipped"

        print(f"Fulfilling order {order_id}...")
        order.status = "processing"
        all_fulfilled = True
        fulfillment_errors = []
        
        try:
            for item in order.items:
                if item.status == "fulfilled":
                    continue # Skip already fulfilled items

                print(f"  Processing item {item.id} (Game: {item.game.name})...")
                try:
                    # Check stock before fulfillment
                    if item.game.stock < item.quantity:
                         raise ValueError(f"Insufficient stock for {item.game.name} (Required: {item.quantity}, Available: {item.game.stock})")
                         
                    if not item.game_account_id: # Needs a digital code
                        item.code = GameShippingService.generate_digital_code(item.game.game_type)
                        item.status = "fulfilled"
                        print(f"    Generated code: {item.code}")
                    else: # Needs direct account credit (simulate for now)
                        # In a real app, call game API here
                        print(f"    Simulating credit for account: {item.game_account_id}")
                        item.status = "fulfilled"
                    
                    # Decrease stock count
                    item.game.stock -= item.quantity
                    db.session.add(item.game) # Add game to session as stock is modified
                    print(f"    Stock updated for {item.game.name}: {item.game.stock}")

                except Exception as item_error:
                    print(f"    Error fulfilling item {item.id}: {item_error}")
                    item.status = "failed"
                    all_fulfilled = False
                    fulfillment_errors.append(f"Item {item.id} ({item.game.name}): {item_error}")

            # Update overall order status
            if all_fulfilled:
                order.status = "completed"
                print(f"Order {order_id} status updated to completed.")
            elif any(i.status == "fulfilled" for i in order.items): # Partially fulfilled
                 order.status = "processing" # Or a custom status like "partially_fulfilled"
                 print(f"Order {order_id} status remains processing (partially fulfilled).")
            else: # All items failed
                 order.status = "failed_fulfillment"
                 print(f"Order {order_id} status updated to failed_fulfillment.")

            db.session.commit()
            print(f"Order {order_id} fulfillment processed.")

            # Send confirmation email only if at least partially successful
            if order.status in ["completed", "processing"]:
                email_sent, email_message = GameShippingService.send_order_confirmation_email(order.id)
                if not email_sent:
                     print(f"Warning: Failed to send confirmation email for order {order.id}: {email_message}")

            return all_fulfilled, f"Order fulfillment complete. Errors: {fulfillment_errors}" if fulfillment_errors else "Order fulfilled successfully"

        except Exception as e:
            db.session.rollback()
            print(f"Critical Error during fulfillment for order {order_id}: {e}")
            # Mark order as failed or requires attention
            order.status = "failed_fulfillment"
            db.session.commit()
            return False, f"Critical fulfillment failed: {str(e)}"

    @staticmethod
    def process_pending_orders():
        """Process all orders that are ready for fulfillment (e.g., payment completed)"""
        # In a real scenario, filter by orders with completed payments
        # For now, let"s assume "pending" orders are ready after checkout simulation
        # Also process orders that previously failed fulfillment
        orders_to_process = Order.query.filter(Order.status.in_(["pending", "failed_fulfillment"])).all()
        print(f"Found {len(orders_to_process)} orders to process.")
        
        results = []
        for order in orders_to_process:
            print(f"Processing order {order.id}...")
            # Ensure payment is completed (simulated check)
            if order.payment and order.payment.status == "completed":
                success, message = GameShippingService.fulfill_order(order.id)
                results.append({
                    "order_id": order.id,
                    "success": success,
                    "message": message
                })
            else:
                 print(f"Skipping order {order.id}, payment not completed.")
                 results.append({
                    "order_id": order.id,
                    "success": False,
                    "message": "Payment not completed"
                })
        
        print(f"Finished processing orders.")
        return results
