from flask import Flask, g
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from config import Config
import os
from datetime import datetime

# Initialize extensions without app instance first
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "الرجاء تسجيل الدخول للوصول إلى هذه الصفحة."
login_manager.login_message_category = "info"

# User loader needs the User model
@login_manager.user_loader
def load_user(user_id):
    # Import User model here, as it"s needed before app context might be fully ready
    from models import User
    return User.query.get(int(user_id))

def create_app(config_class=Config):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)

    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # Initialize extensions with the app instance
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    with app.app_context():
        # Import models *inside the app context* to ensure they are registered
        # with the SQLAlchemy metadata bound to the app before create_all is called.
        import models 

        # Register blueprints *after* models are imported and db initialized
        from routes import main_bp, auth_bp, admin_bp
        from api import api_bp
        from shipping_routes import shipping_bp

        app.register_blueprint(main_bp)
        app.register_blueprint(auth_bp, url_prefix="/auth")
        app.register_blueprint(admin_bp, url_prefix="/admin")
        app.register_blueprint(api_bp, url_prefix="/api")
        app.register_blueprint(shipping_bp, url_prefix="/shipping")

    # Context processor
    @app.context_processor
    def inject_current_year():
        return {"current_year": datetime.utcnow().year}

    # Before request handler
    @app.before_request
    def before_request():
        g.locale = "ar"

    # print(f"App created with DB URI: {app.config["SQLALCHEMY_DATABASE_URI"]}") # Corrected f-string
    return app

