from flask import Blueprint, abort, render_template, request
from flask_login import current_user

from models import Game, TopUpPackage

shop_bp = Blueprint("shop", __name__)


@shop_bp.route("/")
def home():
    games = (
        Game.query.filter_by(is_active=True)
        .order_by(Game.sort_order, Game.id)
        .limit(8)
        .all()
    )
    featured = (
        TopUpPackage.query.join(Game)
        .filter(TopUpPackage.is_active.is_(True), Game.is_active.is_(True))
        .order_by(TopUpPackage.price.desc())
        .limit(6)
        .all()
    )
    completed = 0
    return render_template("home.html", games=games, featured=featured, completed=completed)


@shop_bp.route("/games")
def games():
    category = request.args.get("category", "").strip()
    query = Game.query.filter_by(is_active=True)
    if category:
        query = query.filter_by(category=category)
    games = query.order_by(Game.sort_order, Game.id).all()
    categories = {
        "battle_royale": "باتل رويال",
        "shooter": "تصويب",
        "sports": "رياضة",
        "moba": "MOBA",
        "rpg": "RPG",
        "sandbox": "عالم مفتوح",
    }
    return render_template("games.html", games=games, active_category=category, categories=categories)


@shop_bp.route("/games/<slug>")
def game_detail(slug):
    game = Game.query.filter_by(slug=slug, is_active=True).first()
    if game is None:
        abort(404)
    packages = [p for p in game.packages if p.is_active]
    if not packages:
        abort(404)
    return render_template("game_detail.html", game=game, packages=packages)
