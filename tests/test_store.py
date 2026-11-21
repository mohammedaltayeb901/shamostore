from decimal import Decimal

from conftest import admin_login, login, logout
from extensions import db
from models import Game, Order, TopUpPackage, TopUpRequest, User, WalletTransaction
from services import place_order


def _fund(user, amount):
    user.wallet_move(Decimal(amount), "topup", "إيداع اختباري")
    db.session.commit()


def test_topup_request_waits_for_admin_then_credits_wallet(app, user):
    client = app.test_client()
    login(client, email=user.email)

    client.post(
        "/wallet/topup",
        data={"amount": "20.00", "method": "zain_cash", "reference": "TRX-001", "note": ""},
        follow_redirects=True,
    )
    request_row = TopUpRequest.query.filter_by(user_id=user.id).first()
    assert request_row is not None
    assert request_row.status == "pending"
    assert user.available_balance == Decimal("0.00")

    logout(client)
    admin_login(client)
    client.post(
        f"/admin/topups/{request_row.id}/review",
        data={"action": "approve", "admin_note": "تم التحقق"},
        follow_redirects=True,
    )

    db.session.refresh(user)
    db.session.refresh(request_row)
    assert request_row.status == "approved"
    assert user.available_balance == Decimal("20.00")
    entry = WalletTransaction.query.filter_by(user_id=user.id, kind="topup").one()
    assert entry.amount == Decimal("20.00")
    assert entry.balance_after == Decimal("20.00")


def test_rejected_topup_does_not_credit(app, user):
    client = app.test_client()
    login(client, email=user.email)
    client.post(
        "/wallet/topup",
        data={"amount": "15.00", "method": "bank", "reference": "REF-9", "note": ""},
        follow_redirects=True,
    )
    request_row = TopUpRequest.query.first()

    logout(client)
    admin_login(client)
    client.post(
        f"/admin/topups/{request_row.id}/review",
        data={"action": "reject", "admin_note": "لم يصل المبلغ"},
        follow_redirects=True,
    )

    db.session.refresh(request_row)
    db.session.refresh(user)
    assert request_row.status == "rejected"
    assert user.available_balance == Decimal("0.00")


def test_purchase_deducts_wallet_and_creates_order(app, user, package):
    _fund(user, "10.00")
    order = place_order(user, package, "5123456789", "شكراً")

    assert order.status == "pending"
    assert order.price == Decimal("4.79")
    assert user.available_balance == Decimal("5.21")
    assert Order.query.filter_by(user_id=user.id).count() == 1

    debit = WalletTransaction.query.filter_by(user_id=user.id, kind="purchase").one()
    assert debit.amount == Decimal("-4.79")
    assert debit.balance_after == Decimal("5.21")


def test_purchase_blocks_when_balance_is_low(app, user, package):
    from services import StoreError
    import pytest

    _fund(user, "1.00")
    with pytest.raises(StoreError):
        place_order(user, package, "5123456789")

    assert Order.query.count() == 0
    db.session.refresh(user)
    assert user.available_balance == Decimal("1.00")


def test_order_flow_via_http(app, user, package):
    _fund(user, "10.00")
    client = app.test_client()
    login(client, email=user.email)

    confirm = client.post(
        "/orders/checkout",
        data={"package_id": str(package.id), "player_id": "5123456789", "note": ""},
    )
    assert confirm.status_code == 200
    assert "تأكيد الطلب" in confirm.get_data(as_text=True)

    placed = client.post(
        "/orders/place",
        data={"package_id": str(package.id), "player_id": "5123456789", "note": ""},
        follow_redirects=True,
    )
    assert placed.status_code == 200
    assert "SH-" in placed.get_data(as_text=True)
    assert Order.query.count() == 1


def test_rejecting_order_refunds_wallet(app, user, package):
    _fund(user, "10.00")
    order = place_order(user, package, "5123456789")

    client = app.test_client()
    login(client, email=user.email)
    logout(client)
    admin_login(client)
    client.post(
        f"/admin/orders/{order.id}/status",
        data={"status": "rejected", "admin_note": "معرّف غير صحيح"},
        follow_redirects=True,
    )

    db.session.refresh(order)
    db.session.refresh(user)
    assert order.status == "rejected"
    assert user.available_balance == Decimal("10.00")

    refund = WalletTransaction.query.filter_by(user_id=user.id, kind="refund").one()
    assert refund.amount == Decimal("4.79")


def test_admin_can_adjust_balance(app, user):
    client = app.test_client()
    admin_login(client)
    client.post(
        f"/admin/users/{user.id}/balance",
        data={"amount": "7.50", "reason": "تعويض"},
        follow_redirects=True,
    )
    db.session.refresh(user)
    assert user.available_balance == Decimal("7.50")
