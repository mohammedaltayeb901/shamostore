"""Data models for the Shamostore game top-up store."""

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from flask_login import UserMixin
from sqlalchemy import func
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db, login_manager

MONEY = Decimal("0.01")


def to_money(value):
    """Coerce a value into a two-decimal Decimal amount."""
    return Decimal(str(value)).quantize(MONEY, rounding=ROUND_HALF_UP)


class InsufficientBalance(Exception):
    """Raised when a wallet debit would push the balance below zero."""


ORDER_STATUSES = ("pending", "processing", "completed", "rejected")
ORDER_STATUS_LABELS = {
    "pending": "بانتظار المراجعة",
    "processing": "قيد التنفيذ",
    "completed": "مكتمل",
    "rejected": "مرفوض",
}

TOPUP_STATUS_LABELS = {
    "pending": "بانتظار التأكيد",
    "approved": "مقبول",
    "rejected": "مرفوض",
}

TOPUP_METHODS = {
    "zain_cash": "زين كاش",
    "asiacell": "آسياسيل كاش",
    "fastpay": "FastPay",
    "bank": "تحويل بنكي",
    "usdt": "USDT",
}

# تفاصيل الاستلام لكل طريقة دفع. عدّلها من ملف .env أو هنا بحسب حساباتك.
TOPUP_INSTRUCTIONS = {
    "zain_cash": "حوّل المبلغ إلى رقم زين كاش 0770 000 0000 ثم أدخل رقم عملية التحويل.",
    "asiacell": "حوّل المبلغ إلى رقم آسياسيل 0773 000 0000 ثم أدخل رقم عملية التحويل.",
    "fastpay": "أرسل المبلغ إلى حساب FastPay: shamostore@fastpay ثم أدخل رقم العملية.",
    "bank": "حوّل المبلغ إلى الحساب البنكي IBAN: IQ00 0000 0000 0000 0000 0000 وأدخل رقم الحوالة.",
    "usdt": "أرسل USDT (شبكة TRC20) إلى المحفظة: TXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX وأدخل رمز العملية.",
}

TX_KIND_LABELS = {
    "topup": "شحن رصيد",
    "purchase": "شراء",
    "refund": "استرداد",
    "adjustment": "تعديل إداري",
}


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True, nullable=False)
    email = db.Column(db.String(120), unique=True, index=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, nullable=False, default=False)
    balance = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    transactions = db.relationship(
        "WalletTransaction",
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="WalletTransaction.id.desc()",
    )
    orders = db.relationship(
        "Order",
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="Order.id.desc()",
    )
    topups = db.relationship(
        "TopUpRequest",
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="TopUpRequest.id.desc()",
        foreign_keys="TopUpRequest.user_id",
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def available_balance(self):
        return to_money(self.balance or 0)

    def wallet_move(self, amount, kind, description, order_id=None, topup_id=None):
        """Apply a signed wallet movement and write the ledger row.

        The balance is updated with a single conditional SQL statement so two
        concurrent purchases cannot both spend the same funds: the database
        serialises the writes and the overspend guard fails the second one.
        """
        amount = to_money(amount)
        # SQLite stores NUMERIC as a double, so the sum is rounded to cents in
        # SQL as well. Without it, 0.70 + 0.10 reads as 0.7999999999999999 and a
        # purchase of exactly 0.80 would be refused as insufficient.
        new_balance_sql = func.round(User.balance + amount, 2)
        updated = (
            db.session.query(User)
            .filter(User.id == self.id, new_balance_sql >= 0)
            .update({User.balance: new_balance_sql}, synchronize_session=False)
        )
        if updated != 1:
            raise InsufficientBalance

        db.session.expire(self)
        new_balance = to_money(self.available_balance)
        entry = WalletTransaction(
            user=self,
            amount=amount,
            balance_after=new_balance,
            kind=kind,
            description=description,
            order_id=order_id,
            topup_id=topup_id,
        )
        db.session.add(entry)
        return entry

    def __repr__(self):
        return f"<User {self.email}>"


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


class WalletTransaction(db.Model):
    __tablename__ = "wallet_transactions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    balance_after = db.Column(db.Numeric(12, 2), nullable=False)
    kind = db.Column(db.String(20), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=True)
    topup_id = db.Column(db.Integer, db.ForeignKey("topup_requests.id"), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    user = db.relationship("User", back_populates="transactions")

    @property
    def kind_label(self):
        return TX_KIND_LABELS.get(self.kind, self.kind)


class TopUpRequest(db.Model):
    __tablename__ = "topup_requests"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    method = db.Column(db.String(32), nullable=False)
    reference = db.Column(db.String(64), nullable=False)
    note = db.Column(db.Text)
    status = db.Column(db.String(16), nullable=False, default="pending", index=True)
    admin_note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime)
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    user = db.relationship("User", back_populates="topups", foreign_keys=[user_id])
    reviewer = db.relationship("User", foreign_keys=[reviewed_by_id])

    @property
    def status_label(self):
        return TOPUP_STATUS_LABELS.get(self.status, self.status)

    @property
    def method_label(self):
        return TOPUP_METHODS.get(self.method, self.method)


class Game(db.Model):
    __tablename__ = "games"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(80), unique=True, index=True, nullable=False)
    name = db.Column(db.String(128), nullable=False)
    tagline = db.Column(db.String(160))
    description = db.Column(db.Text)
    category = db.Column(db.String(32), nullable=False, default="battle_royale")
    currency_name = db.Column(db.String(32), nullable=False, default="UC")
    accent = db.Column(db.String(16), nullable=False, default="#7c5cff")
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    packages = db.relationship(
        "TopUpPackage",
        back_populates="game",
        cascade="all, delete-orphan",
        order_by="TopUpPackage.price",
    )

    @property
    def initials(self):
        words = [w for w in self.name.replace(":", " ").split() if w]
        if not words:
            return "?"
        if len(words) == 1:
            return words[0][:2].upper()
        return (words[0][0] + words[1][0]).upper()

    @property
    def active_packages(self):
        return [p for p in self.packages if p.is_active]

    @property
    def cheapest_price(self):
        prices = [p.price for p in self.active_packages]
        return min(prices) if prices else None

    def __repr__(self):
        return f"<Game {self.slug}>"


class TopUpPackage(db.Model):
    __tablename__ = "packages"

    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey("games.id"), nullable=False, index=True)
    label = db.Column(db.String(64), nullable=False)
    amount = db.Column(db.String(32))
    price = db.Column(db.Numeric(12, 2), nullable=False)
    bonus = db.Column(db.String(64))
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    game = db.relationship("Game", back_populates="packages")

    def __repr__(self):
        return f"<TopUpPackage {self.label} {self.price}>"


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    game_id = db.Column(db.Integer, db.ForeignKey("games.id", ondelete="SET NULL"))
    package_id = db.Column(db.Integer, db.ForeignKey("packages.id", ondelete="SET NULL"))
    game_name = db.Column(db.String(128), nullable=False)
    package_label = db.Column(db.String(64), nullable=False)
    player_id = db.Column(db.String(64), nullable=False)
    price = db.Column(db.Numeric(12, 2), nullable=False)
    status = db.Column(db.String(16), nullable=False, default="pending", index=True)
    note = db.Column(db.Text)
    admin_note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    delivered_at = db.Column(db.DateTime)

    user = db.relationship("User", back_populates="orders")
    game = db.relationship("Game")

    @property
    def code(self):
        return f"SH-{self.id:05d}"

    @property
    def status_label(self):
        return ORDER_STATUS_LABELS.get(self.status, self.status)

    def __repr__(self):
        return f"<Order {self.code} {self.status}>"
