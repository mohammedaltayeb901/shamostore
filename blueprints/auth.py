from urllib.parse import urlsplit

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from extensions import db
from forms import LoginForm, RegisterForm
from models import User
from services import create_user

auth_bp = Blueprint("auth", __name__)


def _safe_next(target):
    """Only allow same-site relative redirects after login."""
    if not target:
        return None
    parts = urlsplit(target)
    if parts.scheme or parts.netloc or not target.startswith("/"):
        return None
    return target


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("shop.home"))

    form = RegisterForm()
    if form.validate_on_submit():
        user = create_user(form.username.data, form.email.data, form.password.data)
        db.session.commit()
        login_user(user)
        flash(f"أهلاً بك {user.username}! تم إنشاء حسابك بنجاح.", "success")
        return redirect(url_for("shop.home"))

    return render_template("auth/register.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("shop.home"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip().lower()).first()
        if user is None or not user.check_password(form.password.data):
            flash("البريد الإلكتروني أو كلمة المرور غير صحيح.", "danger")
            return render_template("auth/login.html", form=form), 401
        login_user(user, remember=form.remember_me.data)
        flash(f"مرحباً بعودتك، {user.username}.", "success")
        return redirect(_safe_next(request.args.get("next")) or url_for("shop.home"))

    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("تم تسجيل الخروج.", "info")
    return redirect(url_for("shop.home"))
