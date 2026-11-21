from flask import Blueprint, abort, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from forms import CheckoutForm, PlaceOrderForm
from models import Game, Order, TopUpPackage
from services import StoreError, place_order

orders_bp = Blueprint("orders", __name__)


@orders_bp.route("/orders")
@login_required
def list_orders():
    orders = current_user.orders
    return render_template("orders/list.html", orders=orders)


@orders_bp.route("/orders/checkout", methods=["POST"])
@login_required
def checkout():
    form = CheckoutForm()
    if not form.validate_on_submit():
        for errors in form.errors.values():
            for error in errors:
                flash(error, "danger")
        return redirect(url_for("shop.home"))

    try:
        package_id = int(form.package_id.data)
    except (TypeError, ValueError):
        abort(404)

    package = TopUpPackage.query.get_or_404(package_id)
    game = package.game
    if not package.is_active or not game.is_active:
        abort(404)

    place_form = PlaceOrderForm(
        data={"package_id": package.id, "player_id": form.player_id.data, "note": form.note.data}
    )
    return render_template(
        "orders/checkout.html",
        package=package,
        game=game,
        place_form=place_form,
        total=package.price,
        balance=current_user.available_balance,
        after_balance=current_user.available_balance - package.price,
    )


@orders_bp.route("/orders/place", methods=["POST"])
@login_required
def place():
    form = PlaceOrderForm()
    if not form.validate_on_submit():
        for errors in form.errors.values():
            for error in errors:
                flash(error, "danger")
        return redirect(url_for("shop.games"))

    package = TopUpPackage.query.get_or_404(int(form.package_id.data))
    try:
        order = place_order(current_user, package, form.player_id.data, form.note.data)
    except StoreError as error:
        flash(str(error), "danger")
        return redirect(url_for("shop.game_detail", slug=package.game.slug))

    flash(f"تم إنشاء الطلب {order.code} وسيبدأ تنفيذه قريباً.", "success")
    return redirect(url_for("orders.detail", order_id=order.id))


@orders_bp.route("/orders/<int:order_id>")
@login_required
def detail(order_id):
    order = Order.query.filter_by(id=order_id, user_id=current_user.id).first_or_404()
    return render_template("orders/detail.html", order=order)
