from . import db
from werkzeug.security import generate_password_hash
from datetime import datetime


class User(db.Model):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(20), nullable=False)
    fullname = db.Column(db.String(20), nullable=False)
    address = db.Column(db.String(20), nullable=False)
    pincode = db.Column(db.String(20), nullable=False)

    bookings = db.relationship(
        "Booking", back_populates="user", cascade="all, delete-orphan"
    )


class Parking(db.Model):
    __tablename__ = "parking"
    id = db.Column(db.Integer, primary_key=True)
    primary_location_name = db.Column(db.String(20), nullable=False)
    address = db.Column(db.String(20), nullable=False)
    pin_code = db.Column(db.String(20), nullable=False)
    price = db.Column(db.Float, nullable=False)
    number_of_spots = db.Column(db.Integer, nullable=False)

    spots = db.relationship(
        "parkingSpot", back_populates="parking", cascade="all, delete-orphan"
    )


class parkingSpot(db.Model):
    __tablename__ = "parkingSpot"
    id = db.Column(db.Integer, primary_key=True)
    parking_id = db.Column(db.Integer, db.ForeignKey("parking.id"), nullable=False)
    spot_number = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="A")

    parking = db.relationship("Parking", back_populates="spots")
    bookings = db.relationship(
        "Booking", back_populates="spot", cascade="all, delete-orphan"
    )


class Booking(db.Model):
    __tablename__ = "booking"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    spot_id = db.Column(db.Integer, db.ForeignKey("parkingSpot.id"), nullable=False)
    vehicle_number = db.Column(db.String(20), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="O")
    parking_cost = db.Column(db.Float, nullable=False)

    user = db.relationship("User", back_populates="bookings")
    spot = db.relationship("parkingSpot", back_populates="bookings")


def create_admin():
    admin = User.query.filter_by(username="admin").first()
    if not admin:
        admin = User(
            username="admin",
            fullname="admin",
            address="admin",
            pincode="123456",
            password=generate_password_hash("app123"),
        )
        db.session.add(admin)
        db.session.commit()
