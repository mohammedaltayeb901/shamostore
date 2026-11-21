"""Application factory for Shamostore."""

import os
from decimal import Decimal

from flask import Flask, render_template, send_from_directory

from config import Config
from extensions import csrf, db, login_manager
from models import (
    ORDER_STATUS_LABELS,
    TOPUP_INSTRUCTIONS,
    TOPUP_METHODS,
    TOPUP_STATUS_LABELS,
    TX_KIND_LABELS,
    User,
)
from services import create_user


def create_app(config_class=Config):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)

    database_uri = app.config["SQLALCHEMY_DATABASE_URI"]
    if database_uri.startswith("sqlite:///") and ":memory:" not in database_uri:
        os.makedirs(app.instance_path, exist_ok=True)
    if database_uri.startswith("sqlite"):
        # Let a waiting writer retry for a while instead of failing the request.
        engine_options = dict(app.config.get("SQLALCHEMY_ENGINE_OPTIONS") or {})
        engine_options["connect_args"] = {"timeout": 15}
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = engine_options

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    login_manager.login_view = "auth.login"
    login_manager.login_message = "يرجى تسجيل الدخول للمتابعة."
    login_manager.login_message_category = "warning"

    from blueprints.admin import admin_bp
    from blueprints.auth import auth_bp
    from blueprints.orders import orders_bp
    from blueprints.shop import shop_bp
    from blueprints.wallet import wallet_bp

    app.register_blueprint(shop_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(wallet_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(admin_bp)

    @app.template_filter("money")
    def money_filter(value):
        amount = Decimal(str(value or 0)).quantize(Decimal("0.01"))
        if amount == 0:
            amount = Decimal("0.00")
        return f"{app.config['CURRENCY_SYMBOL']}{amount:,.2f}"

    @app.template_filter("datetime")
    def datetime_filter(value):
        return value.strftime("%Y-%m-%d %H:%M") if value else "—"

    @app.context_processor
    def inject_globals():
        return {
            "store_name": app.config["STORE_NAME"],
            "currency_symbol": app.config["CURRENCY_SYMBOL"],
            "order_status_labels": ORDER_STATUS_LABELS,
            "topup_status_labels": TOPUP_STATUS_LABELS,
            "tx_kind_labels": TX_KIND_LABELS,
            "topup_methods": TOPUP_METHODS,
            "topup_instructions": TOPUP_INSTRUCTIONS,
        }

    @app.route("/favicon.ico")
    def favicon():
        return send_from_directory(app.static_folder, "favicon.svg", mimetype="image/svg+xml")

    @app.errorhandler(404)
    def not_found(error):
        return render_template("error.html", code=404, message="الصفحة التي تبحث عنها غير موجودة."), 404

    @app.errorhandler(403)
    def forbidden(error):
        return render_template("error.html", code=403, message="لا تملك صلاحية الوصول إلى هذه الصفحة."), 403

    @app.cli.command("init-db")
    def init_db_command():
        """Create tables, seed catalogue content, and ensure the admin account."""
        from seed import init_database

        init_database(app)
        print("تم تهيئة قاعدة البيانات بنجاح.")

    @app.cli.command("seed-demo")
    def seed_demo_command():
        """Create the demo customer with credit and sample orders (development only)."""
        from seed import seed_demo

        seed_demo(app)
        print("تم إنشاء الحساب التجريبي: player@shamostore.com")

    @app.cli.command("create-admin")
    def create_admin_command():
        """Create or refresh the admin account from configuration."""
        from seed import check_admin_password, repair_default_admin

        email = app.config["ADMIN_EMAIL"].strip().lower()
        user = User.query.filter_by(email=email).first()
        check_admin_password(app, user)
        if user is None:
            user = create_user(
                app.config["ADMIN_USERNAME"],
                email,
                app.config["ADMIN_PASSWORD"],
                is_admin=True,
            )
        else:
            user.is_admin = True
            if not repair_default_admin(app, user):
                user.set_password(app.config["ADMIN_PASSWORD"])
        db.session.commit()
        print(f"حساب المسؤول جاهز: {email}")

    return app
