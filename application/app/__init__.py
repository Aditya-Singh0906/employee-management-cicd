import os

from flask import Flask
from app.logging_config import configure_logging
from app.api import register_blueprints
from app.config import config_by_name
from app.extensions import db, migrate, jwt, cors, bcrypt
from app import models

def create_app():
    env = os.getenv("FLASK_ENV", "development")

    app = Flask(__name__)

    app.config.from_object(config_by_name[env])

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    cors.init_app(app)
    bcrypt.init_app(app)

    register_blueprints(app)
    
    logger = configure_logging()

    logger.info("Starting Employee Management API...")

    return app