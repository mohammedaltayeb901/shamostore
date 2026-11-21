import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app import create_app  # noqa: E402
from config import TestConfig  # noqa: E402
from extensions import db  # noqa: E402
from models import Game, TopUpPackage, User  # noqa: E402
from seed import init_database  # noqa: E402


@pytest.fixture
def app():
    application = create_app(TestConfig)
    with application.app_context():
        db.create_all()
        admin = User(
            username=TestConfig.ADMIN_USERNAME,
            email=TestConfig.ADMIN_EMAIL,
            is_admin=True,
        )
        admin.set_password(TestConfig.ADMIN_PASSWORD)
        db.session.add(admin)
        db.session.commit()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture
def seeded(app):
    init_database(app)
    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def seeded_client(seeded):
    return seeded.test_client()


def register(client, username="tester", email="tester@example.com", password="Password123"):
    return client.post(
        "/register",
        data={
            "username": username,
            "email": email,
            "password": password,
            "confirm_password": password,
        },
        follow_redirects=True,
    )


def login(client, email="tester@example.com", password="Password123"):
    return client.post(
        "/login",
        data={"email": email, "password": password},
        follow_redirects=True,
    )


def logout(client):
    return client.post("/logout", follow_redirects=True)


def admin_login(client):
    return login(client, email=TestConfig.ADMIN_EMAIL, password=TestConfig.ADMIN_PASSWORD)


@pytest.fixture
def admin_client(app):
    client = app.test_client()
    admin_login(client)
    return client


@pytest.fixture
def user(app):
    user = User(username="walletuser", email="wallet@example.com", balance=0)
    user.set_password("Password123")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def package(app):
    game = Game(
        slug="pubg-mobile",
        name="PUBG Mobile",
        currency_name="UC",
        category="battle_royale",
        accent="#f2a900",
    )
    package = TopUpPackage(game=game, label="325 UC", amount="325", price="4.79")
    db.session.add(package)
    db.session.commit()
    return package
