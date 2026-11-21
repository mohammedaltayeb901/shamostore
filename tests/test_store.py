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


def test_topup_cannot_be_credited_twice(app, user):
    from types import SimpleNamespace

    import pytest
    from services import StoreError, approve_topup

    client = app.test_client()
    login(client, email=user.email)
    client.post(
        "/wallet/topup",
        data={"amount": "20.00", "method": "zain_cash", "reference": "TRX-777", "note": ""},
        follow_redirects=True,
    )
    request_row = TopUpRequest.query.first()

    logout(client)
    admin_login(client)
    client.post(
        f"/admin/topups/{request_row.id}/review",
        data={"action": "approve", "admin_note": ""},
        follow_redirects=True,
    )
    client.post(
        f"/admin/topups/{request_row.id}/review",
        data={"action": "approve", "admin_note": ""},
        follow_redirects=True,
    )

    db.session.refresh(user)
    assert user.available_balance == Decimal("20.00")
    assert WalletTransaction.query.filter_by(user_id=user.id, kind="topup").count() == 1

    admin = User.query.filter_by(is_admin=True).first()
    with pytest.raises(StoreError):
        approve_topup(request_row, admin)

    stale = SimpleNamespace(id=request_row.id, status="pending", amount=Decimal("20.00"), user_id=user.id)
    with pytest.raises(StoreError):
        approve_topup(stale, admin)
    db.session.refresh(user)
    assert user.available_balance == Decimal("20.00")


def test_rejected_order_refunds_only_once(app, user, package):
    from types import SimpleNamespace

    import pytest
    from services import StoreError, update_order_status

    _fund(user, "10.00")
    order = place_order(user, package, "5123456789")

    admin = User.query.filter_by(is_admin=True).first()
    update_order_status(order, "rejected", "معرّف غير صحيح", admin)
    assert update_order_status(order, "rejected", "مرة أخرى", admin).status == "rejected"

    db.session.refresh(user)
    assert user.available_balance == Decimal("10.00")
    assert WalletTransaction.query.filter_by(user_id=user.id, kind="refund").count() == 1

    stale = SimpleNamespace(
        id=order.id,
        status="pending",
        delivered_at=None,
        code=order.code,
        user_id=user.id,
        price=order.price,
    )
    with pytest.raises(StoreError):
        update_order_status(stale, "rejected", "طلب متزامن قديم", admin)

    db.session.refresh(user)
    assert user.available_balance == Decimal("10.00")


def test_wallet_guard_uses_stored_balance_not_stale_memory(app, user):
    import pytest
    from models import InsufficientBalance

    _fund(user, "10.00")
    assert user.available_balance == Decimal("10.00")

    # Another request spent the money after this instance was loaded.
    db.session.query(User).filter_by(id=user.id).update(
        {User.balance: Decimal("1.00")}, synchronize_session=False
    )
    with pytest.raises(InsufficientBalance):
        user.wallet_move(Decimal("-4.79"), "purchase", "شراء بمحاولة متزامنة")
    db.session.rollback()


def test_checkout_get_after_session_expiry_redirects(app, user):
    client = app.test_client()
    login(client, email=user.email)
    response = client.get("/orders/checkout", follow_redirects=True)
    assert response.status_code == 200
    assert "انتهت الجلسة" in response.get_data(as_text=True)


def test_anonymous_game_page_offers_login(seeded_client):
    response = seeded_client.get("/games/pubg-mobile")
    body = response.get_data(as_text=True)
    assert "سجّل الدخول للمتابعة" in body
    assert "متابعة الدفع" not in body


def test_admin_sees_customer_note_on_order(app, user, package):
    _fund(user, "10.00")
    place_order(user, package, "5123456789", note="سيرفر جينشين: Asia")

    admin_client = app.test_client()
    admin_login(admin_client)
    response = admin_client.get("/admin/orders")
    body = response.get_data(as_text=True)
    assert "5123456789" in body
    assert "سيرفر جينشين: Asia" in body


def test_wallet_accepts_purchase_equal_to_float_summed_balance(app, user, package):
    """0.70 + 0.10 must behave as exactly 0.80 (SQLite stores NUMERIC as a double)."""
    user.wallet_move(Decimal("0.70"), "topup", "إيداع")
    user.wallet_move(Decimal("0.10"), "topup", "إيداع")
    db.session.commit()
    assert user.available_balance == Decimal("0.80")

    cheap = TopUpPackage(game=package.game, label="80 نقطة", price=Decimal("0.80"))
    db.session.add(cheap)
    db.session.commit()

    order = place_order(user, cheap, "5123456789")
    assert order.price == Decimal("0.80")
    db.session.refresh(user)
    assert user.available_balance == Decimal("0.00")
