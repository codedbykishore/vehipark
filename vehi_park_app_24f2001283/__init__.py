import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy


curr_dir = os.path.dirname(os.path.abspath(__file__))


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "app123"
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(
        curr_dir, "instance", "parking.db"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["CHART_FOLDER"] = os.path.join("static", "charts")
    os.makedirs(app.config["CHART_FOLDER"], exist_ok=True)
    app.config["PASSWORD_HASH"] = "app123"
    db.init_app(app)
    return app


db = SQLAlchemy()
app = create_app()


from . import models, controllers

app.app_context().push()
with app.app_context():
    db.create_all()
    models.create_admin()
