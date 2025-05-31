from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, current_user, login_required
from models import User, Game, Order, OrderItem, Payment, Cart, CartItem, db
from forms import LoginForm, RegistrationForm, GameSearchForm, CheckoutForm, GameForm # Import GameForm
from app import db # Import db from app

# Create blueprints
main_bp = Blueprint("main", __name__)
auth_bp = Blueprint("auth", __name__)
admin_bp = Blueprint("admin", __name__)

# --- Authentication Routes ---

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        # Create a cart for the new user
        cart = Cart(customer=user)
        db.session.add(cart)
        db.session.commit()
        flash("تهانينا، لقد قمت بالتسجيل بنجاح!", "success")
        return redirect(url_for("auth.login"))
    return render_template("register.html", title="إنشاء حساب", form=form)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None or not user.check_password(form.password.data):
            flash("بريد إلكتروني أو كلمة مرور غير صالحة", "danger")
            return redirect(url_for("auth.login"))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get("next")
        flash("تم تسجيل الدخول بنجاح.", "success")
        return redirect(next_page) if next_page else redirect(url_for("main.index"))
    return render_template("login.html", title="تسجيل الدخول", form=form)

@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("تم تسجيل الخروج بنجاح.", "info")
    return redirect(url_for("main.index"))

# --- Main Routes (Placeholders for now) ---

@main_bp.route("/")
@main_bp.route("/index")
def index():
    # Placeholder: Fetch some games for the homepage
    games = Game.query.filter_by(is_active=True).limit(8).all()
    return render_template("index.html", title="الصفحة الرئيسية", games=games)

@main_bp.route("/games")
def games():
    # Placeholder: Fetch all active games
    page = request.args.get("page", 1, type=int)
    games_pagination = Game.query.filter_by(is_active=True).paginate(page=page, per_page=12, error_out=False)
    games = games_pagination.items
    return render_template("games.html", title="الألعاب", games=games, pagination=games_pagination)

@main_bp.route("/game/<int:id>")
def game_detail(id):
    game = Game.query.get_or_404(id)
    return render_template("game_detail.html", title=game.name, game=game)

@main_bp.route("/cart")
@login_required
def view_cart():
    # Logic to display cart items will be added later
    return render_template("cart.html", title="سلة التسوق")

@main_bp.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    form = CheckoutForm()
    # Logic for checkout process will be added later
    if form.validate_on_submit():
        # Process payment and create order
        flash("تم تقديم الطلب بنجاح!", "success")
        return redirect(url_for("main.order_confirmation")) # Redirect to confirmation page
    return render_template("checkout.html", title="الدفع", form=form)

@main_bp.route("/order_confirmation")
@login_required
def order_confirmation():
    # Placeholder for order confirmation page
    return render_template("order_confirmation.html", title="تأكيد الطلب")

@main_bp.route("/orders")
@login_required
def orders():
    # Placeholder for user's order history
    user_orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template("orders.html", title="طلباتي", orders=user_orders)

@main_bp.route("/order/<int:id>")
@login_required
def order_detail(id):
    order = Order.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    return render_template("order_detail.html", title=f"تفاصيل الطلب #{order.id}", order=order)


# --- Admin Routes (Placeholders for now) ---

# Decorator for admin-only routes
def admin_required(f):
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash("الوصول لهذه الصفحة يتطلب صلاحيات مسؤول.", "danger")
            return redirect(url_for("main.index"))
        return f(*args, **kwargs)
    # Preserve original function name for Flask routing
    decorated_function.__name__ = f.__name__
    return decorated_function

@admin_bp.route("/")
@admin_required
def admin_index():
    # Placeholder for admin dashboard
    return render_template("admin/dashboard.html", title="لوحة تحكم المسؤول")

@admin_bp.route("/games", methods=["GET", "POST"])
@admin_required
def admin_games():
    form = GameForm()
    if form.validate_on_submit():
        game = Game(
            name=form.name.data,
            description=form.description.data,
            price=form.price.data,
            image_url=form.image_url.data,
            category=form.category.data,
            game_type=form.game_type.data,
            region=form.region.data,
            stock=form.stock.data,
            is_active=form.is_active.data
        )
        db.session.add(game)
        db.session.commit()
        flash("تمت إضافة اللعبة بنجاح!", "success")
        return redirect(url_for("admin.admin_games"))
    games = Game.query.all()
    return render_template("admin/games.html", title="إدارة الألعاب", games=games, form=form)

@admin_bp.route("/games/edit/<int:id>", methods=["GET", "POST"])
@admin_required
def admin_edit_game(id):
    game = Game.query.get_or_404(id)
    form = GameForm(obj=game)
    if form.validate_on_submit():
        form.populate_obj(game)
        db.session.commit()
        flash("تم تحديث اللعبة بنجاح!", "success")
        return redirect(url_for("admin.admin_games"))
    return render_template("admin/edit_game.html", title="تعديل اللعبة", form=form, game=game)

@admin_bp.route("/games/delete/<int:id>", methods=["POST"])
@admin_required
def admin_delete_game(id):
    game = Game.query.get_or_404(id)
    db.session.delete(game)
    db.session.commit()
    flash("تم حذف اللعبة بنجاح!", "success")
    return redirect(url_for("admin.admin_games"))

@admin_bp.route("/orders")
@admin_required
def admin_orders():
    # Placeholder for managing orders
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template("admin/orders.html", title="إدارة الطلبات", orders=orders)

@admin_bp.route("/users")
@admin_required
def admin_users():
    # Placeholder for managing users
    users = User.query.all()
    return render_template("admin/users.html", title="إدارة المستخدمين", users=users)
