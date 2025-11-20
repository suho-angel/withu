from flask import Flask, jsonify
from app.config import DevConfig
from app.extensions import db, migrate
from app.routes.auth import bp as auth_bp
from app.routes.contacts import bp as contacts_bp
from app.routes.profile import bp as profile_bp
from app.routes.alerts import bp as alerts_bp
from app.routes.journeys import bp as journeys_bp


def create_app(config_object=DevConfig):
    app = Flask(__name__)
    app.config.from_object(config_object)

    # Extensions
    db.init_app(app)
    migrate.init_app(app, db)

    # Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(contacts_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(alerts_bp)
    app.register_blueprint(journeys_bp)

    # Toy mode: auto create tables if they don't exist (no migrations required)
    with app.app_context():
        try:
            db.create_all()
        except Exception as e:
            # Avoid crashing startup if DB not ready; entrypoint waits for DB anyway
            app.logger.warning(f"db.create_all() skipped due to error: {e}")

    # Health check
    @app.route('/health')
    def health():
        return jsonify({'status': 'ok'}), 200

    return app
