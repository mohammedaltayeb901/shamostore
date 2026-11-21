"""Store business rules: wallet movements, top-up review, order lifecycle.

Every state transition is claimed with a conditional UPDATE before money moves,
so a second request that read the same stale row cannot repeat a credit or a
refund. The claim and the wallet movement commit in one transaction.
"""

from datetime import datetime

from extensions import db
from models import (
    ORDER_STATUSES,
    InsufficientBalance,
    Order,
    TopUpRequest,
    User,
    to_money,
)


class StoreError(Exception):
    """A user-facing store rule was violated."""


def place_order(user, package, player_id, note=""):
    """Charge the wallet and open a pending top-up order."""
    game = package.game
    if not package.is_active or not game.is_active:
        raise StoreError("هذه الباقة غير متاحة حالياً.")

    order = Order(
        user=user,
        game_id=game.id,
        package_id=package.id,
        game_name=game.name,
        package_label=package.label,
        player_id=player_id.strip(),
        price=to_money(package.price),
        note=(note or "").strip() or None,
        status="pending",
    )

    try:
        db.session.add(order)
        db.session.flush()
        user.wallet_move(
            -order.price,
            "purchase",
            f"شراء {package.label} - {game.name}",
            order_id=order.id,
        )
        db.session.commit()
    except InsufficientBalance:
        db.session.rollback()
        raise StoreError("رصيد المحفظة غير كافٍ. يرجى شحن المحفظة أولاً.")
    except Exception:
        db.session.rollback()
        raise

    return order


def update_order_status(order, status, admin_note, admin):
    """Move an order through its lifecycle, refunding a rejected order once."""
    if status not in ORDER_STATUSES:
        raise StoreError("حالة غير معروفة.")

    previous = order.status
    if previous == "rejected" and status != "rejected":
        raise StoreError("لا يمكن إعادة الطلب المرفوض إلى التنفيذ، أنشئ طلباً جديداً.")

    changes = {
        "status": status,
        "admin_note": (admin_note or "").strip() or None,
        "updated_at": datetime.utcnow(),
    }
    if status == "completed" and not order.delivered_at:
        changes["delivered_at"] = datetime.utcnow()

    claimed = (
        db.session.query(Order)
        .filter(Order.id == order.id, Order.status == previous)
        .update(changes, synchronize_session=False)
    )
    if claimed != 1:
        db.session.rollback()
        raise StoreError("تغيّرت حالة هذا الطلب للتو، أعد تحميل الصفحة.")

    try:
        if status == "rejected" and previous != "rejected":
            user = db.session.get(User, order.user_id)
            user.wallet_move(
                order.price,
                "refund",
                f"استرداد قيمة الطلب {order.code}",
                order_id=order.id,
            )
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    db.session.refresh(order)
    return order


def _claim_topup(topup, status, admin, admin_note):
    """Atomically move a pending top-up request to a reviewed state."""
    claimed = (
        db.session.query(TopUpRequest)
        .filter(TopUpRequest.id == topup.id, TopUpRequest.status == "pending")
        .update(
            {
                "status": status,
                "admin_note": (admin_note or "").strip() or None,
                "reviewed_at": datetime.utcnow(),
                "reviewed_by_id": admin.id,
            },
            synchronize_session=False,
        )
    )
    if claimed != 1:
        db.session.rollback()
        raise StoreError("تمت مراجعة هذا الطلب مسبقاً.")
    db.session.refresh(topup)


def approve_topup(topup, admin, admin_note=""):
    _claim_topup(topup, "approved", admin, admin_note)
    try:
        user = db.session.get(User, topup.user_id)
        user.wallet_move(
            topup.amount,
            "topup",
            f"شحن محفظة - {topup.method_label}",
            topup_id=topup.id,
        )
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    db.session.refresh(topup)
    return topup


def reject_topup(topup, admin, admin_note=""):
    _claim_topup(topup, "rejected", admin, admin_note)
    db.session.commit()
    return topup


def adjust_balance(user, amount, reason, admin):
    try:
        user.wallet_move(amount, "adjustment", f"{reason} (بواسطة {admin.username})")
        db.session.commit()
    except InsufficientBalance:
        db.session.rollback()
        raise StoreError("التعديل يجعل الرصيد سالباً.")
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
