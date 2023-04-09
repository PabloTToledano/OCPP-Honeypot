from flask import Flask, render_template, request, send_file, redirect, url_for, flash
from flask_wtf import Form
from flask_sqlalchemy import SQLAlchemy
from flask_login import login_required, LoginManager, current_user
from wtforms.fields import DateField, TimeField
import requests
from datetime import datetime
from auth import User, db


def create_app():
    app = Flask(__name__)

    # Secret bad on purpose
    app.config["SECRET_KEY"] = "password"
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///db.sqlite"
    db.init_app(app)

    # blueprint for auth routes in our app
    from auth import auth as auth_blueprint

    app.register_blueprint(auth_blueprint)

    login_manager = LoginManager()
    login_manager.login_view = "auth.login"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        # since the user_id is just the primary key of our user table, use it in the query for the user
        return User.query.get(int(user_id))

    return app


app = create_app()


@app.route("/")
@login_required
def home():
    return redirect(url_for("auth.login"))


@app.route("/profile")
@login_required
def profile():
    return render_template("profile.html", current_user=current_user)


@app.route("/chargers")
@login_required
def chargers():
    url = "http://localhost:8080/chargers"
    response = requests.get(url)
    json_data = response.json()
    items = []
    for charger in json_data:
        status = "Available"
        reserved_connectors = 0
        for connector in json_data[charger].get("connectors"):
            if json_data[charger]["connectors"][connector] == "Reserved":
                reserved_connectors = reserved_connectors + 1
        if reserved_connectors == len(json_data[charger]["connectors"]):
            color = "bg-danger"
            status = "Reserved"
        else:
            color = "bg-success"

        items.append(
            {
                "color": color,
                "name": json_data[charger].get("ChargerStation").get("model"),
                "reverse_status": status,
                "url": f"charger?id={charger}",
                "button_text": "View",
            }
        )
    return render_template("home.html", items=items, current_user=current_user)


@app.route("/charger")
def charger():
    url = "http://localhost:8080/chargers"
    response = requests.get(url)
    json_data = response.json()
    items = []

    charger_id = request.args.get("id", default="cp", type=str)
    charger = {
        "id": charger_id,
        "name": json_data[charger_id]["ChargerStation"]["vendor_name"],
        "model": json_data[charger_id]["ChargerStation"]["model"],
    }

    for connector in json_data[charger_id].get("connectors"):
        status = json_data[charger_id]["connectors"][connector]
        if status == "Reserved":
            color = "bg-danger"
            button_text = "Cancel reservation"
            url = f"cancelreservation?id={charger_id}&connector={connector}"
        else:
            color = "bg-success"
            button_text = "Make reservation"
            url = f"reserve?id={charger_id}&connector={connector}"
        items.append(
            {
                "color": color,
                "name": f"Connector {connector}",
                "reverse_status": status,
                "url": url,
                "button_text": button_text,
            }
        )

    return render_template(
        "charger.html", items=items, charger=charger, current_user=current_user
    )


class DateForm(Form):
    dt = DateField("DatePicker", format="%Y-%m-%d")
    tp = TimeField("TimePicker")


@app.route("/reserve")
def reserve():
    charger_id = request.args.get("id", type=str)
    print(charger_id)
    connector = request.args.get("connector", default="0", type=str)
    args = {"charger_id": charger_id, "connector": connector}
    form = DateForm()
    return render_template(
        "reserve.html", form=form, args=args, current_user=current_user
    )


@app.route("/reserve", methods=["POST"])
def reserve_post():
    charger_id = request.args.get("id", type=str)
    connector = request.args.get("connector", default="0", type=int)
    form_date = request.form["dt"]
    form_time = request.form["tp"]
    try:
        date = datetime.strptime(form_date + " " + form_time, "%Y-%m-%d %H:%M")
        url = "http://localhost:8080/reserve"
        json = {
            "id": charger_id,
            "connector": int(connector),
            "idToken": "12345",
            "expDate": date.isoformat(),
        }
        response = requests.post(url, json=json)
        json_data = response.json()
        print(json_data)
        return redirect(f"/charger?id={charger_id}", code=302)
    except Exception as e:
        flash("Please enter a date")
        return redirect(url_for("reserve"))


@app.route("/displaymessages")
@login_required
def display_messages():
    charger_id = request.args.get("id", type=str)
    url = "http://localhost:8080/displayMessage"
    json = {"id": charger_id}
    response = requests.get(url, json=json)

    url = "http://localhost:8080/chargers"
    response = requests.get(url)
    json_data = response.json()

    display_messages = json_data[charger_id]["displayMesagges"]
    try:
        last_id = display_messages[-1]["id"]
    except Exception as e:
        last_id = 0
    charger = {
        "id": charger_id,
        "name": json_data[charger_id]["ChargerStation"]["vendor_name"],
        "model": json_data[charger_id]["ChargerStation"]["model"],
        "lastid": last_id,
    }
    return render_template(
        "displaymessages.html",
        msgs=display_messages,
        charger=charger,
        current_user=current_user,
    )


@app.route("/variables")
@login_required
def variables():
    charger_id = request.args.get("id", type=str)
    url = "http://localhost:8080/variables"
    json = {"id": charger_id}
    response = requests.get(url, json=json)
    json_data = response.json()
    variables = json_data["result"]
    print(variables)
    url = "http://localhost:8080/chargers"
    response = requests.get(url)
    json_data = response.json()

    charger = {
        "id": charger_id,
        "name": json_data[charger_id]["ChargerStation"]["vendor_name"],
        "model": json_data[charger_id]["ChargerStation"]["model"],
    }

    return render_template(
        "variables.html",
        msgs=variables,
        charger=charger,
        current_user=current_user,
    )


@app.route("/displaymessages", methods=["POST"])
@login_required
def display_messages_post():
    charger_id = request.args.get("id", type=str)
    last_id = request.args.get("lastid", type=int)
    msg = form_date = request.form["content"]
    url = "http://localhost:8080/displayMessage"
    json = {"id": charger_id, "msg": msg, "msgId": last_id + 1}
    response = requests.post(url, json=json)
    return redirect(f"/displaymessages?id={charger_id}")


@app.route("/cancelreservation")
def cancel_reserve():
    charger_id = request.args.get("id", default="cp", type=str)
    connector = request.args.get("connector", default="0", type=int)
    json = {"id": charger_id, "connector": int(connector)}
    url = "http://localhost:8080/cancelReservation"
    response = requests.post(url, json=json)
    json_data = response.json()
    return redirect(f"/charger?id={charger_id}", code=302)


@app.route("/logo.png")
def get_image():
    return send_file("images/logo.png", mimetype="image/png")


@app.route("/favicon.ico")
def get_ico():
    return send_file("images/favicon.ico", mimetype="image/x-icon")


if __name__ == "__main__":
    app.run(debug=True)
