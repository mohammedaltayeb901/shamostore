from decimal import Decimal, InvalidOperation
from functools import wraps

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

from extensions import db
from forms import GameForm, PackageForm
from models import (
    ORDER_STATUS_LABELS,
    TOPUP_STATUS_LABELS,
    Game,
    Order,
    TopUpPackage,
    TopUpRequest,
    User,
)
from services import StoreError, adjust_balance, approve_topup, reject_topup, update_order_status

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_admin:
            flash("هذه الصفحة مخصصة لمسؤولي المتجر.", "danger")
            return redirect(url_for("shop.home"))
        return view(*args, **kwargs)

    return wrapped


def _decimal(value, default=None):
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError):
        return default


@admin_bp.route("/")
@admin_required
def dashboard():
    revenue_statuses = ("pending", "processing", "completed")
    stats = {
        "users": db.session.query(func.count(User.id)).scalar(),
        "orders": db.session.query(func.count(Order.id)).scalar(),
        "revenue": db.session.query(func.coalesce(func.sum(Order.price), 0))
        .filter(Order.status.in_(revenue_statuses))
        .scalar(),
        "wallet_total": db.session.query(func.coalesce(func.sum(User.balance), 0)).scalar(),
        "pending_orders": db.session.query(func.count(Order.id))
        .filter(Order.status.in_(("pending", "processing")))
        .scalar(),
        "pending_topups": db.session.query(func.count(TopUpRequest.id))
        .filter(TopUpRequest.status == "pending")
        .scalar(),
    }
    recent_orders = Order.query.order_by(Order.id.desc()).limit(8).all()
    recent_topups = (
        TopUpRequest.query.filter_by(status="pending").order_by(TopUpRequest.id.desc()).limit(5).all()
    )
    top_packages = (
        db.session.query(Order.game_name, Order.package_label, func.count(Order.id).label("sold"))
        .group_by(Order.game_name, Order.package_label)
        .order_by(func.count(Order.id).desc())
        .limit(5)
        .all()
    )
    return render_template(
        "admin/dashboard.html",
        stats=stats,
        recent_orders=recent_orders,
        recent_topups=recent_topups,
        top_packages=top_packages,
    )


@admin_bp.route("/games", methods=["GET", "POST"])
@admin_required
def games():
    form = GameForm()
    if form.validate_on_submit():
        game = Game(
            name=form.name.data.strip(),
            slug=form.slug.data.strip().lower(),
            tagline=(form.tagline.data or "").strip() or None,
            description=(form.description.data or "").strip() or None,
            category=form.category.data,
            currency_name=form.currency_name.data.strip(),
            accent=form.accent.data,
            sort_order=int(form.sort_order.data or 0),
            is_active=form.is_active.data,
        )
        db.session.add(game)
        db.session.commit()
        flash(f"تمت إضافة {game.name}.", "success")
        return redirect(url_for("admin.games"))

    all_games = Game.query.order_by(Game.sort_order, Game.id).all()
    return render_template("admin/games.html", form=form, games=all_games, package_form=PackageForm())


@admin_bp.route("/games/<int:game_id>/toggle", methods=["POST"])
@admin_required
def toggle_game(game_id):
    game = Game.query.get_or_404(game_id)
    game.is_active = not game.is_active
    db.session.commit()
    flash(f"{game.name}: {'مفعّلة' if game.is_active else 'موقوفة'}.", "info")
    return redirect(url_for("admin.games"))


@admin_bp.route("/games/<int:game_id>/packages", methods=["POST"])
@admin_required
def add_package(game_id):
    game = Game.query.get_or_404(game_id)
    form = PackageForm()
    if form.validate_on_submit():
        package = TopUpPackage(
            game=game,
            label=form.label.data.strip(),
            amount=(form.amount.data or "").strip() or None,
            price=form.price.data,
            bonus=(form.bonus.data or "").strip() or None,
            sort_order=int(form.sort_order.data or 0),
            is_active=form.is_active.data,
        )
        db.session.add(package)
        db.session.commit()
        flash(f"تمت إضافة باقة {package.label} إلى {game.name}.", "success")
    else:
        flash("تعذر إضافة الباقة، تحقق من الحقول.", "danger")
    return redirect(url_for("admin.games"))


@admin_bp.route("/packages/<int:package_id>/toggle", methods=["POST"])
@admin_required
def toggle_package(package_id):
    package = TopUpPackage.query.get_or_404(package_id)
    package.is_active = not package.is_active
    db.session.commit()
    return redirect(url_for("admin.games"))


@admin_bp.route("/packages/<int:package_id>/update", methods=["POST"])
@admin_required
def update_package(package_id):
    package = TopUpPackage.query.get_or_404(package_id)
    price = _decimal(request.form.get("price"))
    if price is None or price <= 0:
        flash("سعر غير صالح.", "danger")
    else:
        package.price = price
        label = (request.form.get("label") or "").strip()
        if label:
            package.label = label
        db.session.commit()
        flash("تم تحديث الباقة.", "success")
    return redirect(url_for("admin.games"))


@admin_bp.route("/orders")
@admin_required
def orders():
    status = request.args.get("status", "").strip()
    query = Order.query
    if status in ORDER_STATUS_LABELS:
        query = query.filter_by(status=status)
    order_list = query.order_by(Order.id.desc()).limit(200).all()
    return render_template(
        "admin/orders.html",
        orders=order_list,
        active_status=status,
        statuses=ORDER_STATUS_LABELS,
    )


@admin_bp.route("/orders/<int:order_id>/status", methods=["POST"])
@admin_required
def order_status(order_id):
    order = Order.query.get_or_404(order_id)
    status = request.form.get("status", "")
    try:
        update_order_status(order, status, request.form.get("admin_note"), current_user)
        flash(f"تم تحديث الطلب {order.code} إلى «{order.status_label}».", "success")
    except StoreError as error:
        flash(str(error), "danger")
    return redirect(request.referrer or url_for("admin.orders"))


@admin_bp.route("/topups")
@admin_required
def topups():
    status = request.args.get("status", "").strip()
    query = TopUpRequest.query
    if status in TOPUP_STATUS_LABELS:
        query = query.filter_by(status=status)
    requests = query.order_by(TopUpRequest.id.desc()).limit(200).all()
    return render_template(
        "admin/topups.html",
        topups=requests,
        active_status=status,
        statuses=TOPUP_STATUS_LABELS,
    )


@admin_bp.route("/topups/<int:topup_id>/review", methods=["POST"])
@admin_required
def review_topup(topup_id):
    topup = TopUpRequest.query.get_or_404(topup_id)
    action = request.form.get("action")
    note = request.form.get("admin_note")
    try:
        if action == "approve":
            approve_topup(topup, current_user, note)
            flash(f"تم قبول طلب {topup.user.username} وإضافة {topup.amount}.", "success")
        elif action == "reject":
            reject_topup(topup, current_user, note)
            flash("تم رفض طلب الشحن.", "info")
        else:
            flash("إجراء غير معروف.", "danger")
    except StoreError as error:
        flash(str(error), "danger")
    return redirect(request.referrer or url_for("admin.topups"))


@admin_bp.route("/users")
@admin_required
def users():
    search = request.args.get("q", "").strip()
    query = User.query
    if search:
        query = query.filter(
            User.username.ilike(f"%{search}%") | User.email.ilike(f"%{search}%")
        )
    user_list = query.order_by(User.id.desc()).limit(200).all()
    return render_template("admin/users.html", users=user_list, search=search)


@admin_bp.route("/users/<int:user_id>/balance", methods=["POST"])
@admin_required
def user_balance(user_id):
    user = User.query.get_or_404(user_id)
    amount = _decimal(request.form.get("amount"))
    reason = (request.form.get("reason") or "").strip()
    if amount is None or amount == 0 or not reason:
        flash("أدخل مبلغاً غير صفري وسبباً واضحاً.", "danger")
    else:
        try:
            adjust_balance(user, amount, reason, current_user)
            flash(f"تم تعديل رصيد {user.username}.", "success")
        except StoreError as error:
            flash(str(error), "danger")
    return redirect(request.referrer or url_for("admin.users"))
