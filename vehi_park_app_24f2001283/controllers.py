import os
from math import ceil
from datetime import datetime

from flask import render_template, redirect, url_for, request, session, flash
from sqlalchemy import or_, cast, String

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from werkzeug.security import generate_password_hash, check_password_hash

from . import app, db
from .models import User, Parking, parkingSpot, Booking


@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()

        if user:
            if not check_password_hash(user.password, password):
                flash("Incorrect password. Please try again.", "danger")
                return render_template("login.html")

            session["username"] = username
            session["user_id"] = user.id

            flash("Login successful", "success")
            return redirect(url_for("admin" if user.username == "admin" else "user"))

        else:
            flash("User not found. Please check your username.", "danger")
            return render_template("login.html")

    return render_template("login.html")


@app.route("/admin", methods=["GET"])
def admin():
    if "username" not in session:
        return redirect(url_for("login"))

    return render_template("admin.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        fullname = request.form["fullname"]
        address = request.form["address"]
        pincode = request.form["pincode"]
        
        user = User(
            username=username,
            password=generate_password_hash(password),
            fullname=fullname,
            address=address,
            pincode=pincode,
        )
        db.session.add(user)
        db.session.commit()

        if session.get("username") == "admin":
            flash("User registered successfully.", "success")
            return redirect(url_for("admin_user"))
        else:
            flash("Registration successful. Please log in.", "success")
            return redirect(url_for("login"))

    return render_template("signup.html")


@app.route("/parking", methods=["GET", "POST"])
def parking():
    if "username" not in session:
        return redirect(url_for("login"))

    parkings = Parking.query.all()
    parking_spots = {}
    available_counts = {}
    users = User.query.all()

    for parking in parkings:
        spots = parkingSpot.query.filter_by(parking_id=parking.id).all()

        parking_spots[parking.id] = spots

        available_counts[parking.id] = parkingSpot.query.filter_by(
            parking_id=parking.id, status="A"
        ).count()

    return render_template(
        "parking.html",
        parkings=parkings,
        available_counts=available_counts,
        parking_spots=parking_spots,
        users=users,
    )


@app.route("/add_parking", methods=["GET", "POST"])
def add_parking():
    if "username" not in session:
        return redirect(url_for("login"))
    if request.method == "POST":
        primary_location_name = request.form["primary_location_name"]
        address = request.form["address"]
        pin_code = request.form["pin_code"]
        price = int(request.form["price"])
        number_of_spots = request.form["number_of_spots"]

        new_parking = Parking(
            primary_location_name=primary_location_name,
            address=address,
            pin_code=pin_code,
            price=price,
            number_of_spots=number_of_spots,
        )
        db.session.add(new_parking)
        db.session.flush()
        for i in range(1, int(number_of_spots) + 1):
            spot = parkingSpot(parking_id=new_parking.id, spot_number=i, status="A")
            db.session.add(spot)
        db.session.commit()
        return redirect(url_for("parking"))
    return redirect(url_for("parking"))

    return render_template(
        "parking.html", parkings=parkings, available_counts=available_counts
    )


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.route("/edit_parking/<int:parking_id>", methods=["GET", "POST"])
def edit_parking(parking_id):
    if "username" not in session or session["username"] != "admin":
        return redirect(url_for("login"))

    parking = Parking.query.get_or_404(parking_id)

    if request.method == "POST":
        parking.primary_location_name = request.form["primary_location_name"]
        parking.address = request.form["address"]
        parking.pin_code = request.form["pin_code"]
        parking.price = float(request.form["price"])
        new_spot_count = int(request.form["number_of_spots"])

        current_spots = {spot.spot_number: spot for spot in parking.spots}

        for i in range(1, new_spot_count + 1):
            if i not in current_spots:
                new_spot = parkingSpot(parking_id=parking.id, spot_number=i, status="A")
                db.session.add(new_spot)

        for spot_number, spot in current_spots.items():
            if spot_number > new_spot_count:
                has_history = Booking.query.filter_by(spot_id=spot.id).first()
                if spot.status == "A" and not has_history:
                    db.session.delete(spot)

        parking.number_of_spots = new_spot_count
        db.session.commit()
        return redirect(url_for("parking"))

    return render_template("edit_parking.html", parking=parking)


@app.route("/delete_parking/<int:parking_id>", methods=["POST", "GET"])
def delete_parking(parking_id):
    if "username" not in session or session["username"] != "admin":
        return redirect(url_for("login"))

    parking = Parking.query.get_or_404(parking_id)
    if parking.spots:
        for spot in parking.spots:
            if spot.status == "O":
                flash("Cannot delete parking with occupied spots.", "error")
                return redirect(url_for("parking"))
            db.session.delete(spot)
    db.session.delete(parking)
    db.session.commit()
    flash("Parking deleted successfully.", "success")
    return redirect(url_for("parking"))


@app.route("/user", methods=["GET", "POST"])
def user():
    if "username" not in session:
        return redirect(url_for("login"))
    username = session["username"]
    query = request.args.get("query")
    if query:
        parkings = Parking.query.filter(
            (Parking.primary_location_name.ilike(f"%{query}%"))
            | (Parking.address.ilike(f"%{query}%"))
            | (Parking.pin_code.ilike(f"%{query}%"))
        ).all()
    else:
        parkings = Parking.query.all()
    available_counts = {}
    for parking in parkings:
        available_counts[parking.id] = parkingSpot.query.filter_by(
            parking_id=parking.id, status="A"
        ).count()
    return render_template(
        "user.html",
        username=username,
        parkings=parkings,
        available_counts=available_counts,
    )


@app.route("/booking/<int:spot_id>", methods=["GET", "POST"])
def booking(spot_id):
    if "username" not in session:
        return redirect(url_for("login"))

    parking = parkingSpot.query.filter_by(id=spot_id).first()
    if not parking:
        return redirect(url_for("user"))

    if request.method == "POST":
        vehicle_number = request.form["vehicle_number"]
        user_id = request.form.get("user_id") or session.get("user_id")
        user_id = int(user_id)

        available_spot = parkingSpot.query.filter_by(
            parking_id=spot_id, status="A"
        ).first()
        if not available_spot:
            return "No available spots", 400

        available_spot.status = "O"
        booking = Booking(
            user_id=user_id,
            spot_id=available_spot.id,
            vehicle_number=vehicle_number,
            start_time=datetime.now(),
            end_time=None,
            parking_cost=parking.parking.price,
        )

        db.session.add(booking)
        db.session.commit()

        if session.get("username") == "admin":
            return redirect(url_for("admin"))
        return redirect(url_for("user"))

    users = []
    if session["username"] == "admin":
        users = User.query.filter(User.username != "admin").all()

    return render_template(
        "booking.html",
        parking=parking,
        spot_id=spot_id,
        user_id=session.get("user_id"),
        users=users,
    )


@app.route("/history", methods=["GET", "POST"])
def history():
    if "username" not in session:
        return redirect(url_for("login"))
    bookings = Booking.query.filter_by(user_id=session["user_id"]).all()

    return render_template("booking_history.html", bookings=bookings)


@app.route("/summary")
def user_summary():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    user = User.query.get(user_id)

    monthly_counts = [0] * 12
    monthly_expenses = [0] * 12

    bookings = Booking.query.filter_by(user_id=user_id).all()

    for booking in bookings:
        if booking.start_time:
            month = booking.start_time.month
            monthly_counts[month - 1] += 1
            monthly_expenses[month - 1] += booking.parking_cost or 0

    print("Monthly Counts:", monthly_counts)
    print("Monthly Expenses:", monthly_expenses)

    return render_template(
        "user_summary.html",
        user=user,
        monthly_counts=monthly_counts,
        monthly_expenses=monthly_expenses,
    )


@app.route("/admin/search")
def admin_search():
    query = request.args.get("query", "").strip()
    user_results = []
    booking_results = []
    parking_results = []

    if query:
        user_results = User.query.filter(
            or_(
                User.username.ilike(f"%{query}%"),
                User.fullname.ilike(f"%{query}%"),
                User.address.ilike(f"%{query}%"),
                User.pincode.ilike(f"%{query}%"),
            )
        ).all()

        booking_results = Booking.query.filter(
            or_(
                Booking.vehicle_number.ilike(f"%{query}%"),
                cast(Booking.id, String).ilike(f"%{query}%"),
                Booking.status.ilike(f"%{query}%"),
                cast(Booking.parking_cost, String).ilike(f"%{query}%"),
                cast(Booking.start_time, String).ilike(f"%{query}%"),
                cast(Booking.end_time, String).ilike(f"%{query}%"),
            )
        ).all()

        parking_results = Parking.query.filter(
            or_(
                Parking.primary_location_name.ilike(f"%{query}%"),
                Parking.address.ilike(f"%{query}%"),
                Parking.pin_code.ilike(f"%{query}%"),
                cast(Parking.price, String).ilike(f"%{query}%"),
                cast(Parking.number_of_spots, String).ilike(f"%{query}%"),
            )
        ).all()

    return render_template(
        "admin_search.html",
        query=query,
        users=user_results,
        bookings=booking_results,
        parkings=parking_results,
    )


@app.route("/delete_spot/<int:spot_id>", methods=["POST"])
def delete_spot(spot_id):
    if "username" not in session:
        return redirect(url_for("login"))

    spot = parkingSpot.query.get_or_404(spot_id)

    if spot.status == "O":
        flash("Cannot delete a spot with active bookings.", "error")
        return redirect(url_for("parking"))

    db.session.delete(spot)
    db.session.commit()
    flash("Parking spot deleted successfully.", "success")
    return redirect(url_for("parking"))


from math import ceil

@app.route("/release_booking/<int:booking_id>", methods=["GET", "POST"])
def release_booking(booking_id):
    if "username" not in session:
        return redirect(url_for("login"))

    booking = Booking.query.get_or_404(booking_id)
    if booking.end_time:
        flash("Booking already released", "error")
        return redirect(url_for("history"))

    booking.end_time = datetime.now()
    duration = booking.end_time - booking.start_time
    hours = ceil(duration.total_seconds() / 3600)
    booking.parking_cost = hours * booking.spot.parking.price

  
    if booking.parking_cost < booking.spot.parking.price:
        booking.parking_cost = booking.spot.parking.price

    booking.spot.status = "A"
    booking.status = "Released"
    db.session.commit()

    return redirect(url_for("history"))



@app.route("/admin_user", methods=["GET", "POST"])
def admin_user():
    if "username" not in session or session["username"] != "admin":
        return redirect(url_for("login"))

    users = User.query.filter(User.username != "admin").all()

    return render_template("manage_user.html", users=users)


@app.route("/edit_user/<int:user_id>", methods=["GET", "POST"])
def edit_user(user_id):
    if "username" not in session or session["username"] != "admin":
        return redirect(url_for("login"))

    user = User.query.get_or_404(user_id)

    if request.method == "POST":
        user.username = request.form["username"]
        user.fullname = request.form["fullname"]
        user.address = request.form["address"]
        user.pincode = request.form["pincode"]
        db.session.commit()
        return redirect(url_for("admin_user"))

    return render_template("edit_user.html", user=user)


@app.route("/delete_user/<int:user_id>", methods=["GET"])
def delete_user(user_id):
    if "username" not in session or session["username"] != "admin":
        return redirect(url_for("login"))

    user = User.query.get_or_404(user_id)

    active_bookings = Booking.query.filter_by(user_id=user_id, status="O").first()
    if active_bookings:
        flash("Cannot delete user with active bookings.", "error")
        return redirect(url_for("admin_user"))

    db.session.delete(user)
    db.session.commit()
    flash("User deleted successfully.", "success")
    return redirect(url_for("admin_user"))


@app.route("/admin/summary", methods=["GET", "POST"])
def admin_summary():
    if "username" not in session or session["username"] != "admin":
        return redirect(url_for("login"))

    lots = Parking.query.order_by(Parking.primary_location_name).all()

    lot_names = []
    available_counts = []
    occupied_counts = []
    revenue_by_lot = []

    for lot in lots:
        lot_names.append(lot.primary_location_name)
        available = parkingSpot.query.filter_by(parking_id=lot.id, status="A").count()
        occupied = parkingSpot.query.filter_by(parking_id=lot.id, status="O").count()
        available_counts.append(available)
        occupied_counts.append(occupied)

        total_revenue = 0
        for spot in lot.spots:
            for booking in spot.bookings:
                if booking.status == "Released":
                    total_revenue += booking.parking_cost
        revenue_by_lot.append(total_revenue)

    os.makedirs(app.config["CHART_FOLDER"], exist_ok=True)

    # Bar Chart
    plt.figure(figsize=(10, 6))
    plt.bar(lot_names, available_counts, label="Available Spots")
    plt.bar(lot_names, occupied_counts, bottom=available_counts, label="Occupied Spots")
    plt.xlabel("Parking Lots")
    plt.ylabel("Number of Spots")
    plt.title("Available vs Occupied Parking Spots")
    plt.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()
    bar_chart_path = os.path.join(app.config["CHART_FOLDER"], "bar_chart.png")
    plt.savefig(bar_chart_path)
    plt.close()

    # Pie Chart (safe check)
    plt.figure(figsize=(8, 6))
    if revenue_by_lot and sum(revenue_by_lot) > 0:
        plt.pie(revenue_by_lot, labels=lot_names, autopct="%1.1f%%")
        plt.title("Revenue by Parking Lot")
    else:
        plt.text(0.5, 0.5, 'No Revenue Data', ha='center', va='center', fontsize=14)
        plt.axis('off')  # Hide axis if no pie
    plt.tight_layout()
    pie_chart_path = os.path.join(app.config["CHART_FOLDER"], "pie_chart.png")
    plt.savefig(pie_chart_path)
    plt.close()

    bar_chart_url = url_for("static", filename="charts/bar_chart.png")
    pie_chart_url = url_for("static", filename="charts/pie_chart.png")

    return render_template(
        "admin_summary.html",
        lots=lots,
        available_counts=available_counts,
        occupied_counts=occupied_counts,
        revenue_by_lot=revenue_by_lot,
        bar_chart_url=bar_chart_url,
        pie_chart_url=pie_chart_url,
    )



@app.route("/admin/booking/<int:spot_id>", methods=["GET", "POST"])
def admin_booking(spot_id):
    if session.get("username") != "admin":
        return redirect(url_for("login"))

    parking = parkingSpot.query.filter_by(id=spot_id).first()
    if not parking:
        return redirect(url_for("admin"))

    if request.method == "POST":
        vehicle_number = request.form["vehicle_number"]
        user_id = int(request.form["user_id"])

        available_spot = parkingSpot.query.filter_by(
            parking_id=parking.parking_id, status="A"
        ).first()

        if not available_spot:
            flash("No available spots", "danger")
            return redirect(url_for("admin"))

        available_spot.status = "O"
        booking = Booking(
            user_id=user_id,
            spot_id=available_spot.id,
            vehicle_number=vehicle_number,
            start_time=datetime.now(),
            end_time=None,
            parking_cost=parking.parking.price,
        )

        db.session.add(booking)
        db.session.commit()
        flash("Booking successful", "success")
        return redirect(url_for("admin"))

    users = User.query.filter(User.username != "admin").all()

    return render_template(
        "admin_booking.html", parking=parking, spot_id=spot_id, users=users
    )
