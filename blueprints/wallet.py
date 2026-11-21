from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

from extensions import db
from forms import TopUpForm
from models import ORDER_STATUSES, Order, TopUpRequest

wallet_bp = Blueprint("wallet", __name__)


@wallet_bp.route("/wallet")
@login_required
def index():
    transactions = current_user.transactions[:50]
    topups = current_user.topups[:20]
    spent = (
        db.session.query(func.coalesce(func.sum(Order.price), 0))
        .filter(Order.user_id == current_user.id, Order.status != "rejected")
        .scalar()
    )
    stats = {
        "spent": spent,
        "orders": db.session.query(func.count(Order.id)).filter(Order.user_id == current_user.id).scalar(),
        "completed": db.session.query(func.count(Order.id))
        .filter(Order.user_id == current_user.id, Order.status.in_(("processing", "completed")))
        .scalar(),
        "pending": db.session.query(func.count(TopUpRequest.id))
        .filter(TopUpRequest.user_id == current_user.id, TopUpRequest.status == "pending")
        .scalar(),
    }
    return render_template(
        "wallet/index.html",
        transactions=transactions,
        topups=topups,
        stats=stats,
        order_statuses=ORDER_STATUSES,
    )


@wallet_bp.route("/wallet/topup", methods=["GET", "POST"])
@login_required
def topup():
    form = TopUpForm()

    if form.validate_on_submit():
        request_row = TopUpRequest(
            user=current_user,
            amount=form.amount.data,
            method=form.method.data,
            reference=form.reference.data.strip(),
            note=(form.note.data or "").strip() or None,
        )
        db.session.add(request_row)
        db.session.commit()
        flash("تم استلام طلب الشحن، سيُراجع خلال دقائق ويُضاف الرصيد.", "success")
        return redirect(url_for("wallet.index"))

    return render_template("wallet/topup.html", form=form)


@wallet_bp.route("/wallet/topup/<int:topup_id>/cancel", methods=["POST"])
@login_required
def cancel_topup(topup_id):
    request_row = TopUpRequest.query.filter_by(id=topup_id, user_id=current_user.id).first_or_404()
    if request_row.status != "pending":
        flash("لا يمكن إلغاء طلب تمت مراجعته.", "warning")
    else:
        db.session.delete(request_row)
        db.session.commit()
        flash("تم إلغاء طلب الشحن.", "info")
    return redirect(url_for("wallet.index"))
