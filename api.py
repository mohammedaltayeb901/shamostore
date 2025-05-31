from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from models import db, Game, Cart, CartItem, Order, OrderItem, Payment

api_bp = Blueprint("api", __name__)

# --- Game API Endpoints ---

@api_bp.route("/games", methods=["GET"])
def get_games():
    """Get a list of active games"""
    try:
        # Add filtering/pagination later if needed
        games = Game.query.filter_by(is_active=True).all()
        games_data = [
            {
                "id": game.id,
                "name": game.name,
                "price": game.price,
                "image_url": game.image_url,
                "category": game.category,
                "game_type": game.game_type,
            }
            for game in games
        ]
        return jsonify({"success": True, "data": games_data})
    except Exception as e:
        # Log the error in a real application
        print(f"Error fetching games: {e}")
        return jsonify({"success": False, "message": "حدث خطأ أثناء جلب الألعاب."}), 500

@api_bp.route("/games/<int:id>", methods=["GET"])
def get_game_detail(id):
    """Get details for a specific game"""
    try:
        game = Game.query.get_or_404(id)
        if not game.is_active:
             return jsonify({"success": False, "message": "اللعبة غير متوفرة."}), 404
             
        game_data = {
            "id": game.id,
            "name": game.name,
            "description": game.description,
            "price": game.price,
            "image_url": game.image_url,
            "category": game.category,
            "game_type": game.game_type,
            "region": game.region,
            "stock": game.stock, # Consider if stock should be public
        }
        return jsonify({"success": True, "data": game_data})
    except Exception as e:
        print(f"Error fetching game detail: {e}")
        return jsonify({"success": False, "message": "حدث خطأ أثناء جلب تفاصيل اللعبة."}), 500

# --- Cart API Endpoints ---

@api_bp.route("/cart", methods=["GET"])
@login_required
def view_cart_api():
    """Get the current user's cart contents"""
    try:
        cart = current_user.cart
        if not cart:
            # Create cart if it doesn't exist (should have been created on registration)
            cart = Cart(customer=current_user)
            db.session.add(cart)
            db.session.commit()
            
        cart_items = CartItem.query.filter_by(cart_id=cart.id).all()
        items_data = []
        total = 0
        for item in cart_items:
            game = item.game
            item_total = item.quantity * game.price
            items_data.append({
                "item_id": item.id,
                "game_id": game.id,
                "name": game.name,
                "price": game.price,
                "quantity": item.quantity,
                "image_url": game.image_url,
                "item_total": round(item_total, 2),
                "game_account_id": item.game_account_id
            })
            total += item_total
            
        return jsonify({
            "success": True, 
            "data": {
                "items": items_data, 
                "total": round(total, 2)
            }
        })
    except Exception as e:
        print(f"Error fetching cart: {e}")
        return jsonify({"success": False, "message": "حدث خطأ أثناء جلب سلة التسوق."}), 500

@api_bp.route("/cart/add", methods=["POST"])
@login_required
def add_to_cart_api():
    """Add an item to the cart"""
    data = request.get_json()
    if not data or "game_id" not in data or "quantity" not in data:
        return jsonify({"success": False, "message": "بيانات غير كافية لإضافة المنتج للسلة."}), 400

    try:
        game_id = int(data["game_id"])
        quantity = int(data["quantity"])
        game_account_id = data.get("game_account_id") # Optional

        if quantity <= 0:
             return jsonify({"success": False, "message": "الكمية يجب أن تكون أكبر من صفر."}), 400

        game = Game.query.get(game_id)
        if not game or not game.is_active:
            return jsonify({"success": False, "message": "اللعبة غير متوفرة."}), 404
        
        # Check stock if necessary (implement stock logic later)
        # if game.stock < quantity:
        #     return jsonify({"success": False, "message": "الكمية المطلوبة غير متوفرة في المخزون."}), 400

        cart = current_user.cart
        if not cart:
            cart = Cart(customer=current_user)
            db.session.add(cart)
            # Need to flush to get cart.id before adding item
            db.session.flush()

        # Check if item already exists in cart
        existing_item = CartItem.query.filter_by(cart_id=cart.id, game_id=game_id).first()

        if existing_item:
            existing_item.quantity += quantity
            # Update game_account_id if provided in the new request
            if game_account_id:
                 existing_item.game_account_id = game_account_id
        else:
            new_item = CartItem(cart_id=cart.id, game_id=game_id, quantity=quantity, game_account_id=game_account_id)
            db.session.add(new_item)
        
        db.session.commit()
        return jsonify({"success": True, "message": "تمت إضافة المنتج إلى السلة بنجاح."})

    except ValueError:
         return jsonify({"success": False, "message": "معرف اللعبة أو الكمية غير صالح."}), 400
    except Exception as e:
        db.session.rollback() # Rollback in case of error
        print(f"Error adding to cart: {e}")
        return jsonify({"success": False, "message": "حدث خطأ أثناء إضافة المنتج للسلة."}), 500

@api_bp.route("/cart/update/<int:item_id>", methods=["PUT"])
@login_required
def update_cart_item_api(item_id):
    """Update quantity of an item in the cart"""
    data = request.get_json()
    if not data or "quantity" not in data:
        return jsonify({"success": False, "message": "الكمية مطلوبة للتحديث."}), 400

    try:
        quantity = int(data["quantity"])
        if quantity <= 0:
            # If quantity is zero or less, remove the item
            return remove_from_cart_api(item_id)

        cart = current_user.cart
        if not cart:
             return jsonify({"success": False, "message": "لم يتم العثور على سلة التسوق."}), 404
             
        item = CartItem.query.filter_by(id=item_id, cart_id=cart.id).first()
        if not item:
            return jsonify({"success": False, "message": "لم يتم العثور على المنتج في السلة."}), 404
        
        # Check stock if necessary
        # game = item.game
        # if game.stock < quantity:
        #     return jsonify({"success": False, "message": "الكمية المطلوبة غير متوفرة في المخزون."}), 400

        item.quantity = quantity
        db.session.commit()
        return jsonify({"success": True, "message": "تم تحديث كمية المنتج بنجاح."})

    except ValueError:
         return jsonify({"success": False, "message": "الكمية غير صالحة."}), 400
    except Exception as e:
        db.session.rollback()
        print(f"Error updating cart item: {e}")
        return jsonify({"success": False, "message": "حدث خطأ أثناء تحديث المنتج في السلة."}), 500

@api_bp.route("/cart/remove/<int:item_id>", methods=["DELETE"])
@login_required
def remove_from_cart_api(item_id):
    """Remove an item from the cart"""
    try:
        cart = current_user.cart
        if not cart:
             return jsonify({"success": False, "message": "لم يتم العثور على سلة التسوق."}), 404
             
        item = CartItem.query.filter_by(id=item_id, cart_id=cart.id).first()
        if not item:
            return jsonify({"success": False, "message": "لم يتم العثور على المنتج في السلة."}), 404

        db.session.delete(item)
        db.session.commit()
        return jsonify({"success": True, "message": "تمت إزالة المنتج من السلة بنجاح."})

    except Exception as e:
        db.session.rollback()
        print(f"Error removing from cart: {e}")
        return jsonify({"success": False, "message": "حدث خطأ أثناء إزالة المنتج من السلة."}), 500

@api_bp.route("/cart/clear", methods=["DELETE"])
@login_required
def clear_cart_api():
    """Clear all items from the cart"""
    try:
        cart = current_user.cart
        if cart:
            CartItem.query.filter_by(cart_id=cart.id).delete()
            db.session.commit()
        return jsonify({"success": True, "message": "تم إفراغ سلة التسوق بنجاح."})
    except Exception as e:
        db.session.rollback()
        print(f"Error clearing cart: {e}")
        return jsonify({"success": False, "message": "حدث خطأ أثناء إفراغ سلة التسوق."}), 500

# --- Order API Endpoints ---

@api_bp.route("/orders", methods=["GET"])
@login_required
def get_orders_api():
    """Get the current user's order history"""
    try:
        orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
        orders_data = []
        for order in orders:
            items_count = OrderItem.query.filter_by(order_id=order.id).count()
            orders_data.append({
                "id": order.id,
                "status": order.status,
                "total_amount": order.total_amount,
                "created_at": order.created_at.isoformat(),
                "items_count": items_count
            })
        return jsonify({"success": True, "data": orders_data})
    except Exception as e:
        print(f"Error fetching orders: {e}")
        return jsonify({"success": False, "message": "حدث خطأ أثناء جلب سجل الطلبات."}), 500

@api_bp.route("/orders/<int:id>", methods=["GET"])
@login_required
def get_order_detail_api(id):
    """Get details for a specific order"""
    try:
        order = Order.query.filter_by(id=id, user_id=current_user.id).first_or_404()
        items = OrderItem.query.filter_by(order_id=order.id).all()
        items_data = [
            {
                "item_id": item.id,
                "game_id": item.game_id,
                "name": item.game.name,
                "price": item.price,
                "quantity": item.quantity,
                "status": item.status,
                "code": item.code, # Be careful about exposing codes directly
                "game_account_id": item.game_account_id,
                "image_url": item.game.image_url
            }
            for item in items
        ]
        payment_data = None
        if order.payment:
            payment_data = {
                "method": order.payment.payment_method,
                "status": order.payment.status,
                "transaction_id": order.payment.transaction_id
            }
            
        order_data = {
            "id": order.id,
            "status": order.status,
            "total_amount": order.total_amount,
            "created_at": order.created_at.isoformat(),
            "items": items_data,
            "payment": payment_data
        }
        return jsonify({"success": True, "data": order_data})
    except Exception as e:
        print(f"Error fetching order detail: {e}")
        return jsonify({"success": False, "message": "حدث خطأ أثناء جلب تفاصيل الطلب."}), 500

@api_bp.route("/checkout", methods=["POST"])
@login_required
def checkout_api():
    """Process checkout and create an order"""
    data = request.get_json()
    if not data or "payment_method" not in data:
        return jsonify({"success": False, "message": "طريقة الدفع مطلوبة."}), 400

    try:
        cart = current_user.cart
        if not cart or not cart.items.first(): # Check if cart exists and is not empty
            return jsonify({"success": False, "message": "سلة التسوق فارغة."}), 400

        # Calculate total amount from cart items
        total_amount = 0
        cart_items = CartItem.query.filter_by(cart_id=cart.id).all()
        if not cart_items:
             return jsonify({"success": False, "message": "سلة التسوق فارغة."}), 400
             
        for item in cart_items:
            # Check stock before creating order
            # if item.game.stock < item.quantity:
            #     return jsonify({"success": False, "message": f"الكمية المطلوبة للعبة '{item.game.name}' غير متوفرة."}), 400
            total_amount += item.quantity * item.game.price
        
        total_amount = round(total_amount, 2)

        # Create the order
        new_order = Order(user_id=current_user.id, total_amount=total_amount, status="pending")
        db.session.add(new_order)
        db.session.flush() # Get the order ID before creating items

        # Move items from cart to order items
        for item in cart_items:
            order_item = OrderItem(
                order_id=new_order.id,
                game_id=item.game_id,
                quantity=item.quantity,
                price=item.game.price, # Store price at time of order
                game_account_id=item.game_account_id,
                status="pending"
            )
            db.session.add(order_item)
            # Optional: Decrease stock count here
            # item.game.stock -= item.quantity

        # Create payment record (placeholder - real integration needed)
        payment = Payment(
            order_id=new_order.id,
            payment_method=data["payment_method"],
            amount=total_amount,
            status="pending" # Status will be updated by payment gateway callback/webhook
        )
        db.session.add(payment)

        # Clear the cart
        CartItem.query.filter_by(cart_id=cart.id).delete()

        db.session.commit()
        
        # Placeholder: In a real app, redirect to payment gateway or process payment here
        # For now, we simulate successful payment processing and fulfillment
        payment.status = "completed"
        payment.transaction_id = f"FAKE_TRANS_{new_order.id}"
        db.session.commit()
        
        # Trigger fulfillment (optional, could be a background task)
        from shipping import GameShippingService # Import here to avoid circular dependency
        GameShippingService.fulfill_order(new_order.id)

        return jsonify({"success": True, "message": "تم إنشاء الطلب بنجاح.", "order_id": new_order.id})

    except Exception as e:
        db.session.rollback()
        print(f"Error during checkout: {e}")
        return jsonify({"success": False, "message": "حدث خطأ أثناء عملية الدفع."}), 500
