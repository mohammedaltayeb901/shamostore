from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from models import Order, OrderItem, db
from shipping import GameShippingService
from routes import admin_required # Import admin_required decorator

shipping_bp = Blueprint("shipping", __name__, url_prefix="/shipping")

@shipping_bp.route("/fulfill/<int:order_id>", methods=["POST"])
@admin_required
def fulfill_order_route(order_id):
    """API endpoint to manually trigger fulfillment for an order."""
    try:
        success, message = GameShippingService.fulfill_order(order_id)
        if success:
            return jsonify({"success": True, "message": message})
        else:
            return jsonify({"success": False, "message": message}), 400 # Or 500 depending on error type
    except Exception as e:
        print(f"Error in fulfill_order_route for order {order_id}: {e}")
        return jsonify({"success": False, "message": "حدث خطأ داخلي أثناء محاولة تلبية الطلب."}), 500

@shipping_bp.route("/process_pending", methods=["POST"])
@admin_required
def process_pending_orders_route():
    """API endpoint to trigger processing of all pending orders."""
    try:
        results = GameShippingService.process_pending_orders()
        return jsonify({
            "success": True,
            "message": f"تمت معالجة {len(results)} طلبات معلقة.",
            "data": results
        })
    except Exception as e:
        print(f"Error in process_pending_orders_route: {e}")
        return jsonify({"success": False, "message": "حدث خطأ داخلي أثناء معالجة الطلبات المعلقة."}), 500

@shipping_bp.route("/generate_code", methods=["POST"])
@admin_required
def generate_code_route():
    """API endpoint to generate a sample digital code."""
    data = request.get_json()
    game_type = data.get("game_type", "generic") # Get game_type from request or default
    try:
        code = GameShippingService.generate_digital_code(game_type)
        return jsonify({"success": True, "data": {"code": code}})
    except Exception as e:
        print(f"Error in generate_code_route: {e}")
        return jsonify({"success": False, "message": "حدث خطأ أثناء توليد الكود."}), 500

@shipping_bp.route("/send_email/<int:order_id>", methods=["POST"])
@admin_required
def send_email_route(order_id):
    """API endpoint to manually trigger sending the confirmation email."""
    try:
        success, message = GameShippingService.send_order_confirmation_email(order_id)
        if success:
            return jsonify({"success": True, "message": message})
        else:
            # Use 404 if order not found, 500 for other errors
            status_code = 404 if "not found" in message.lower() else 500
            return jsonify({"success": False, "message": message}), status_code
    except Exception as e:
        print(f"Error in send_email_route for order {order_id}: {e}")
        return jsonify({"success": False, "message": "حدث خطأ داخلي أثناء إرسال البريد الإلكتروني."}), 500
