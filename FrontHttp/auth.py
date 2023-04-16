from flask import (
    Blueprint,
    Flask,
    render_template,
    request,
    send_file,
    redirect,
    url_for,
    flash,
)
from flask_login import login_user, login_required, logout_user, UserMixin, current_user
from flask_wtf import Form
from flask_sqlalchemy import SQLAlchemy
from wtforms.fields import DateField, TimeField
import requests
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash


auth = Blueprint("auth", __name__)
db = SQLAlchemy()


class User(UserMixin, db.Model):
    id = db.Column(
        db.Integer, primary_key=True
    )  # primary keys are required by SQLAlchemy
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(1000))


class UserFake(UserMixin):
    id = "1"
    email = "admin@admin.es"
    password = "admin"
    name = "admin"


@auth.route("/login")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("chargers"))
    else:
        return render_template("login.html")


@auth.route("/login", methods=["POST"])
def login_post():
    if current_user.is_authenticated:
        return redirect(url_for("chargers"))
    else:
        email = request.form.get("email")
        password = request.form.get("password")
        remember = True if request.form.get("remember") else False

        user = User.query.filter_by(email=email).first()

        # check if the user actually exists
        # take the user-supplied password, hash it, and compare it to the hashed password in the database
        if not user or not check_password_hash(user.password, password):
            flash("Please check your login details and try again.")
            return redirect(
                url_for("auth.login")
            )  # if the user doesn't exist or password is wrong, reload the page

        # if the above check passes, then we know the user has the right credentials
        login_user(user, remember=remember)
        return redirect(url_for("chargers"))


@auth.route("/signup")
def signup():
    return render_template("signup.html")


@auth.route("/signup", methods=["POST"])
def signup_post():
    # code to validate and add user to database goes here
    email = request.form.get("email")
    name = request.form.get("name")
    password = request.form.get("password")

    user = User.query.filter_by(
        email=email
    ).first()  # if this returns a user, then the email already exists in database

    if (
        user
    ):  # if a user is found, we want to redirect back to signup page so user can try again
        flash("Email address already exists")
        return redirect(url_for("auth.signup"))

    # create a new user with the form data. Hash the password so the plaintext version isn't saved.
    new_user = User(
        email=email,
        name=name,
        password=generate_password_hash(password, method="sha256"),
    )

    # add the new user to the database
    db.session.add(new_user)
    db.session.commit()

    return redirect(url_for("home"))


@auth.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
