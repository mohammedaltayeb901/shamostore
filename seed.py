"""Seed the store catalogue, admin account, and a demo customer."""

from datetime import datetime, timedelta
from decimal import Decimal

from extensions import db
from models import Game, Order, TopUpPackage, TopUpRequest, User
from services import create_user

CATALOGUE = [
    {
        "slug": "pubg-mobile",
        "name": "PUBG Mobile",
        "tagline": "شدات ببجي موبايل بأسعار منافسة",
        "description": "اشحن شدات PUBG Mobile مباشرة إلى حسابك بمعرّف اللاعب فقط. تُضاف الشدات خلال دقائق وتظهر في حسابك داخل اللعبة.",
        "category": "battle_royale",
        "currency_name": "UC",
        "accent": "#f2a900",
        "packages": [
            ("60 UC", "60", "0.99", None),
            ("325 UC", "325", "4.79", None),
            ("660 UC", "660", "9.49", "+60"),
            ("1800 UC", "1800", "24.99", "+300"),
            ("3850 UC", "3850", "49.99", "+800"),
            ("8100 UC", "8100", "99.99", None),
        ],
    },
    {
        "slug": "free-fire",
        "name": "Free Fire",
        "tagline": "جواهر فري فاير في ثوانٍ",
        "description": "شحن جواهر Free Fire بالمعرّف الرقمي للحساب. جميع الباقات تعمل على السيرفر العالمي والشرق الأوسط.",
        "category": "battle_royale",
        "currency_name": "جواهر",
        "accent": "#ff4d4d",
        "packages": [
            ("100 جوهرة", "100", "0.89", None),
            ("310 جوهرة", "310", "2.49", None),
            ("520 جوهرة", "520", "3.99", "+20"),
            ("1060 جوهرة", "1060", "7.99", None),
            ("2180 جوهرة", "2180", "15.99", "+100"),
        ],
    },
    {
        "slug": "efootball",
        "name": "eFootball",
        "tagline": "عملات eFootball لحسابك",
        "description": "اشحن عملات eFootball لبناء فريقك والتعاقد مع أفضل اللاعبين.",
        "category": "sports",
        "currency_name": "عملات",
        "accent": "#00b4d8",
        "packages": [
            ("100 عملة", "100", "0.99", None),
            ("500 عملة", "500", "4.49", None),
            ("1200 عملة", "1200", "9.99", "+100"),
        ],
    },
    {
        "slug": "cod-mobile",
        "name": "Call of Duty: Mobile",
        "tagline": "CP لشراء الصناديق والباتل باس",
        "description": "شحن COD Points مباشرة إلى حساب Call of Duty: Mobile.",
        "category": "shooter",
        "currency_name": "CP",
        "accent": "#6ee7b7",
        "packages": [
            ("80 CP", "80", "0.99", None),
            ("420 CP", "420", "4.99", None),
            ("880 CP", "880", "9.99", "+80"),
        ],
    },
    {
        "slug": "genshin-impact",
        "name": "Genshin Impact",
        "tagline": "كريستالات جينشين",
        "description": "اشحن Genesis Crystals لسحب الشخصيات والأسلحة. تحتاج معرّف UID وسيرفر حسابك.",
        "category": "rpg",
        "currency_name": "كريستال",
        "accent": "#8b5cf6",
        "packages": [
            ("60 كريستال", "60", "0.99", None),
            ("330 كريستال", "330", "4.99", None),
            ("1090 كريستال", "1090", "14.99", "+110"),
        ],
    },
    {
        "slug": "roblox",
        "name": "Roblox",
        "tagline": "روبوكس لحسابك",
        "description": "شحن Robux لحساب Roblox بالاسم أو المعرّف.",
        "category": "sandbox",
        "currency_name": "Robux",
        "accent": "#e2231a",
        "packages": [
            ("80 Robux", "80", "0.99", None),
            ("400 Robux", "400", "4.99", None),
            ("800 Robux", "800", "9.99", "+80"),
        ],
    },
    {
        "slug": "mobile-legends",
        "name": "Mobile Legends",
        "tagline": "ألماس موبايل ليجندز",
        "description": "اشحن Diamonds لشراء الأبطال والجلود في Mobile Legends: Bang Bang.",
        "category": "moba",
        "currency_name": "Diamond",
        "accent": "#3b82f6",
        "packages": [
            ("86 Diamond", "86", "0.99", None),
            ("172 Diamond", "172", "1.99", None),
            ("429 Diamond", "429", "4.99", None),
        ],
    },
    {
        "slug": "fortnite",
        "name": "Fortnite",
        "tagline": "V-Bucks لكل المنصات",
        "description": "شحن V-Bucks عبر حساب Epic Games، تُسلّم على شكل بطاقة رقمية.",
        "category": "battle_royale",
        "currency_name": "V-Bucks",
        "accent": "#22d3ee",
        "packages": [
            ("1000 V-Bucks", "1000", "7.99", None),
            ("2800 V-Bucks", "2800", "19.99", None),
        ],
    },
]


def init_database(app):
    """Create the tables, the catalogue, and the admin account only.

    No customer account is created here, so a production install never ships a
    funded login. Demo data lives in seed_demo() and is opt-in.
    """
    db.create_all()

    email = app.config["ADMIN_EMAIL"].strip().lower()
    admin = User.query.filter_by(email=email).first()
    if admin is None:
        admin = create_user(
            app.config["ADMIN_USERNAME"],
            email,
            app.config["ADMIN_PASSWORD"],
            is_admin=True,
        )
        db.session.add(admin)
    else:
        admin.is_admin = True

    if Game.query.count() == 0:
        for index, entry in enumerate(CATALOGUE):
            game = Game(
                slug=entry["slug"],
                name=entry["name"],
                tagline=entry["tagline"],
                description=entry["description"],
                category=entry["category"],
                currency_name=entry["currency_name"],
                accent=entry["accent"],
                sort_order=index,
                is_active=True,
            )
            db.session.add(game)
            for order_index, (label, amount, price, bonus) in enumerate(entry["packages"]):
                game.packages.append(
                    TopUpPackage(
                        label=label,
                        amount=amount,
                        price=Decimal(price),
                        bonus=bonus,
                        sort_order=order_index,
                        is_active=True,
                    )
                )

    db.session.commit()


def seed_demo(app, email="player@shamostore.com"):
    """Create a demo customer with credit and sample history (development only)."""
    if not app.config.get("ENABLE_DEMO_ACCOUNT", True):
        raise RuntimeError("الحساب التجريبي معطّل (ENABLE_DEMO_ACCOUNT=false).")

    demo = User.query.filter_by(email=email).first()
    if demo is None:
        demo = create_user("player", email, "Player@12345")
        db.session.add(demo)
        db.session.flush()
        demo.wallet_move(Decimal("25.00"), "topup", "رصيد تجريبي للعرض")

        pubg = Game.query.filter_by(slug="pubg-mobile").first()
        free_fire = Game.query.filter_by(slug="free-fire").first()
        if pubg and free_fire:
            started = datetime.utcnow() - timedelta(days=2)
            first = Order(
                user=demo,
                game_id=pubg.id,
                game_name=pubg.name,
                package_label="325 UC",
                player_id="5123456789",
                price=Decimal("4.79"),
                status="completed",
                created_at=started,
                updated_at=started,
                delivered_at=started,
            )
            second = Order(
                user=demo,
                game_id=free_fire.id,
                game_name=free_fire.name,
                package_label="310 جوهرة",
                player_id="778899123",
                price=Decimal("2.49"),
                status="pending",
                created_at=datetime.utcnow() - timedelta(hours=3),
            )
            db.session.add_all([first, second])
            demo.wallet_move(Decimal("-4.79"), "purchase", "شراء 325 UC - PUBG Mobile")
            demo.wallet_move(Decimal("-2.49"), "purchase", "شراء 310 جوهرة - Free Fire")
            db.session.add(
                TopUpRequest(
                    user=demo,
                    amount=Decimal("5.00"),
                    method="zain_cash",
                    reference="ZAIN-99120",
                    note="تحويل من رقم 0770xxxxxxx",
                )
            )

    db.session.commit()
    return demo


if __name__ == "__main__":
    from app import create_app

    application = create_app()
    with application.app_context():
        init_database(application)
        seed_demo(application)
        print("Seed complete.")
