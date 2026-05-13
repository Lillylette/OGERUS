import os
import re
from flask import Flask
from models import db
from flask_login import LoginManager
from config import Config


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.jinja_env.filters['regex_replace'] = lambda s, find, replace: re.sub(find, replace, s)
    # Создаём папку для загрузок
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Инициализация расширений
    db.init_app(app)

    login_manager = LoginManager(app)
    login_manager.login_view = 'auth.login'

    @login_manager.user_loader
    def load_user(user_id):
        from models import User
        return db.session.get(User, int(user_id))

    # Регистрация Blueprints
    from blueprints.main import main_bp
    from blueprints.auth import auth_bp
    from blueprints.profile import profile_bp
    from blueprints.tasks import tasks_bp
    from blueprints.theory import theory_bp
    from blueprints.api_progress import api_progress_bp
    from blueprints.punctuation_test import punctuation_test_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(theory_bp)
    app.register_blueprint(api_progress_bp)
    app.register_blueprint(punctuation_test_bp)


    # Создание таблиц
    with app.app_context():
        db.create_all()

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)