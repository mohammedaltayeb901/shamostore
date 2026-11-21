from conftest import admin_login, login, register
from models import User
from extensions import db


def test_register_creates_user_with_hashed_password(client):
    response = register(client)
    assert response.status_code == 200

    user = User.query.filter_by(email="tester@example.com").first()
    assert user is not None
    assert user.username == "tester"
    assert user.password_hash != "Password123"
    assert user.check_password("Password123")
    assert user.balance == 0


def test_register_rejects_duplicate_email(client):
    register(client)
    client.post("/logout")
    response = register(client, username="other")
    assert "مسجل بالفعل" in response.get_data(as_text=True)
    assert User.query.filter_by(email="tester@example.com").count() == 1


def test_register_rejects_short_password(client):
    register(client, password="short")
    assert User.query.filter_by(email="tester@example.com").first() is None


def test_login_with_email_and_password(client):
    register(client)
    from conftest import logout

    logout(client)

    bad = client.post("/login", data={"email": "tester@example.com", "password": "wrong-pass"})
    assert bad.status_code == 401

    good = client.post(
        "/login",
        data={"email": "tester@example.com", "password": "Password123"},
        follow_redirects=True,
    )
    assert good.status_code == 200
    assert "مرحباً بعودتك" in good.get_data(as_text=True)


def test_login_is_case_insensitive_for_email(client):
    register(client)
    client.post("/logout")
    response = login(client, email="TESTER@EXAMPLE.COM")
    assert response.status_code == 200


def test_protected_page_requires_login(client):
    response = client.get("/wallet", follow_redirects=True)
    assert "تسجيل الدخول" in response.get_data(as_text=True)


def test_admin_area_is_forbidden_for_customers(seeded_client):
    seeded_client.post(
        "/register",
        data={
            "username": "shopper",
            "email": "shopper@example.com",
            "password": "Password123",
            "confirm_password": "Password123",
        },
    )
    response = seeded_client.get("/admin/", follow_redirects=True)
    assert "مخصصة لمسؤولي المتجر" in response.get_data(as_text=True)


def test_admin_can_open_dashboard(admin_client):
    response = admin_client.get("/admin/")
    assert response.status_code == 200
    assert "نظرة عامة" in response.get_data(as_text=True)


def test_init_refuses_default_admin_password_when_disallowed(app):
    import pytest
    from seed import init_database

    app.config["ALLOW_DEFAULT_ADMIN"] = False
    app.config["ADMIN_PASSWORD"] = "Admin@12345"
    from extensions import db
    from models import User

    db.session.query(User).delete()
    db.session.commit()

    with pytest.raises(RuntimeError):
        init_database(app)
    assert User.query.filter_by(email=app.config["ADMIN_EMAIL"]).first() is None

    app.config["ADMIN_PASSWORD"] = "Str0ng-Password!"
    init_database(app)
    assert User.query.filter_by(email=app.config["ADMIN_EMAIL"]).first() is not None


def test_existing_default_admin_is_refused_on_public_deploy(app):
    import pytest
    from seed import init_database
    from models import User

    app.config["ALLOW_DEFAULT_ADMIN"] = False
    admin = User.query.filter_by(email=app.config["ADMIN_EMAIL"]).first()
    assert admin.check_password("Admin@12345")

    with pytest.raises(RuntimeError):
        init_database(app)

    app.config["ADMIN_PASSWORD"] = "Str0ng-Password!"
    from services import create_user

    other = create_user("newadmin", "new@example.com", "Str0ng-Password!", is_admin=True)
    db.session.add(other)
    db.session.commit()
    assert other.is_admin


def test_strong_password_repairs_a_default_hash_admin(app):
    from seed import init_database
    from models import User

    admin = User.query.filter_by(email=app.config["ADMIN_EMAIL"]).first()
    assert admin.check_password("Admin@12345")

    app.config["ALLOW_DEFAULT_ADMIN"] = False
    app.config["ADMIN_PASSWORD"] = "Str0ng-Password!"
    init_database(app)

    db.session.refresh(admin)
    assert admin.check_password("Str0ng-Password!")
    assert not admin.check_password("Admin@12345")
    assert admin.is_admin


def test_custom_admin_password_is_not_overwritten_by_init(app):
    from seed import init_database
    from models import User

    admin = User.query.filter_by(email=app.config["ADMIN_EMAIL"]).first()
    admin.set_password("My-Own-Password-9")
    db.session.commit()

    app.config["ALLOW_DEFAULT_ADMIN"] = False
    app.config["ADMIN_PASSWORD"] = "Str0ng-Password!"
    init_database(app)

    db.session.refresh(admin)
    assert admin.check_password("My-Own-Password-9")


def test_create_admin_command_refuses_default_password(app):
    from models import User

    app.config["ALLOW_DEFAULT_ADMIN"] = False
    runner = app.test_cli_runner()
    result = runner.invoke(args=["create-admin"])
    assert result.exit_code != 0
    assert "كلمة المرور الافتراضية" in str(result.exception) or "كلمة المرور الافتراضية" in result.output
    assert User.query.filter_by(email=app.config["ADMIN_EMAIL"]).first().check_password("Admin@12345")
