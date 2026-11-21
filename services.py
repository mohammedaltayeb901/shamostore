"""Store business rules: wallet movements, top-up review, order lifecycle."""

from datetime import datetime

from extensions import db
from models import InsufficientBalance, Order, TopUpRequest, User


class StoreError(Exception):
    """A user-facing store rule was violated."""


def place_order(user, package, player_id, note=""):
    """Charge the wallet and open a pending top-up order."""
    game = package.game
    if not package.is_active or not game.is_active:
        raise StoreError("هذه الباقة غير متاحة حالياً.")

    price = package.price
    order = Order(
        user=user,
        game_id=game.id,
        package_id=package.id,
        game_name=game.name,
        package_label=package.label,
        player_id=player_id.strip(),
        price=price,
        note=(note or "").strip() or None,
        status="pending",
    )
    db.session.add(order)
    db.session.flush()

    try:
        user.wallet_move(
            -price,
            "purchase",
            f"شراء {package.label} - {game.name}",
            order_id=order.id,
        )
    except InsufficientBalance:
        db.session.rollback()
        raise StoreError("رصيد المحفظة غير كافٍ. يرجى شحن المحفظة أولاً.")

    db.session.commit()
    return order


def update_order_status(order, status, admin_note, admin):
    """Move an order through its lifecycle, refunding a rejected order once."""
    if status not in ("pending", "processing", "completed", "rejected"):
        raise StoreError("حالة غير معروفة.")

    if status == "rejected" and order.status != "rejected":
        order.user.wallet_move(
            order.price,
            "refund",
            f"استرداد قيمة الطلب {order.code}",
            order_id=order.id,
        )
    if order.status == "rejected" and status != "rejected":
        raise StoreError("لا يمكن إعادة الطلب المرفوض إلى التنفيذ، أنشئ طلباً جديداً.")

    order.status = status
    order.admin_note = (admin_note or "").strip() or None
    if status == "completed" and not order.delivered_at:
        order.delivered_at = datetime.utcnow()
    db.session.commit()
    return order


def approve_topup(topup, admin, admin_note=""):
    if topup.status != "pending":
        raise StoreError("تمت مراجعة هذا الطلب مسبقاً.")
    topup.status = "approved"
    topup.admin_note = (admin_note or "").strip() or None
    topup.reviewed_at = datetime.utcnow()
    topup.reviewed_by_id = admin.id
    topup.user.wallet_move(
        topup.amount,
        "topup",
        f"شحن محفظة - {topup.method_label}",
        topup_id=topup.id,
    )
    db.session.commit()
    return topup


def reject_topup(topup, admin, admin_note=""):
    if topup.status != "pending":
        raise StoreError("تمت مراجعة هذا الطلب مسبقاً.")
    topup.status = "rejected"
    topup.admin_note = (admin_note or "").strip() or None
    topup.reviewed_at = datetime.utcnow()
    topup.reviewed_by_id = admin.id
    db.session.commit()
    return topup


def adjust_balance(user, amount, reason, admin):
    try:
        user.wallet_move(amount, "adjustment", f"{reason} (بواسطة {admin.username})")
    except InsufficientBalance:
        db.session.rollback()
        raise StoreError("التعديل يجعل الرصيد سالباً.")
    db.session.commit()
    return user


def create_user(username, email, password, is_admin=False, balance=0):
    user = User(
        username=username.strip(),
        email=email.strip().lower(),
        is_admin=is_admin,
        balance=balance,
    )
    user.set_password(password)
    db.session.add(user)
    return user
