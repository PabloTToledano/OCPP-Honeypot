from flask import (
    Flask,
    render_template,
    request,
    send_file,
    redirect,
    url_for,
    flash,
    has_request_context,
)
from flask_wtf import Form
from flask_sqlalchemy import SQLAlchemy
from flask_login import login_required, LoginManager, current_user, login_user
from wtforms.fields import DateField, TimeField
import requests
import logging
import os
from datetime import datetime
from auth import User, db, UserFake
from flask.logging import default_handler

logging.basicConfig()
host_backend = "csms1"


class RequestFormatter(logging.Formatter):
    def format(self, record):
        if has_request_context():
            record.url = request.url
            record.remote_addr = request.remote_addr
        else:
            record.url = None
            record.remote_addr = None

        return super().format(record)


def create_app():
    app = Flask(__name__)

    # Secret bad on purpose
    app.config["SECRET_KEY"] = "password"
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///db.sqlite"
    app.name = "e-Quijote"
    db.init_app(app)

    with app.app_context():
        db.create_all()

    formatter = RequestFormatter(
        "[%(asctime)s] %(remote_addr)s requested %(url)s\n"
        "%(levelname)s in %(module)s: %(message)s"
    )
    default_handler.setFormatter(formatter)

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
def home():
    if os.getenv("NO_LOG"):
        app.logger.info("No log detected")
        user = UserFake()
        login_user(user, remember=True)
    return redirect(url_for("auth.login"))


@app.route("/profile")
@login_required
def profile():
    return render_template("profile.html", current_user=current_user)


@app.route("/chargers")
@login_required
def chargers():
    url = f"http://{host_backend}:8080/chargers"
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
@login_required
def charger():
    url = f"http://{host_backend}:8080/chargers"
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
        match status:
            case "Reserved":
                color = "bg-warning"
                buttons = [
                    {
                        "button_text": "Cancel reservation",
                        "url": f"cancelreservation?id={charger_id}&connector={connector}",
                    },
                    {
                        "button_text": "Change Status",
                        "url": f"status?id={charger_id}&connector={connector}",
                    },
                ]
            case "Available":
                color = "bg-success"
                buttons = [
                    {
                        "button_text": "Make reservation",
                        "url": f"reserve?id={charger_id}&connector={connector}",
                    },
                    {
                        "button_text": "Change Status",
                        "url": f"status?id={charger_id}&connector={connector}",
                    },
                ]
            case "Unavailable":
                color = "bg-danger"
                buttons = [
                    {
                        "button_text": "Change Status",
                        "url": f"status?id={charger_id}&connector={connector}",
                    }
                ]
                button_text = "Make reservation"
                url = f"status?id={charger_id}&connector={connector}"
        items.append(
            {
                "color": color,
                "name": f"Connector {connector}",
                "reverse_status": status,
                "buttons": buttons,
            }
        )

    return render_template(
        "charger.html", items=items, charger=charger, current_user=current_user
    )


class DateForm(Form):
    dt = DateField("DatePicker", format="%Y-%m-%d")
    tp = TimeField("TimePicker")


@app.route("/status")
@login_required
def status():
    charger_id = request.args.get("id", type=str)
    connector = request.args.get("connector", default="0", type=str)
    args = {"charger_id": charger_id, "connector": connector}

    return render_template("status.html", args=args, current_user=current_user)


@app.route("/status", methods=["POST"])
@login_required
def status_post():
    charger_id = request.args.get("id", type=str)
    connector = request.args.get("connector", default="0", type=str)
    args = {"charger_id": charger_id, "connector": connector}

    new_status = request.form["inputStatus"]

    url = f"http://{host_backend}:8080/status"
    json = {"id": charger_id, "connectorId": connector, "operationalStatus": new_status}
    response = requests.post(url, json=json)

    return redirect(f"/charger?id={charger_id}")


@app.route("/trigger")
@login_required
def trigger():
    charger_id = request.args.get("id", type=str)
    charger = {"id": charger_id}

    return render_template("trigger.html", charger=charger, current_user=current_user)


@app.route("/trigger", methods=["POST"])
@login_required
def trigger_post():
    charger_id = request.args.get("id", type=str)
    charger = {"id": charger_id}

    message_type = request.form["inputType"]

    url = f"http://{host_backend}:8080/triggerMessage"
    json = {"id": charger_id, "requestedMessage": message_type}
    response = requests.post(url, json=json)
    flash("Trigger sent")
    return redirect(f"/trigger?id={charger_id}")


@app.route("/update")
@login_required
def update():
    charger_id = request.args.get("id", type=str)
    args = {"charger_id": charger_id}

    return render_template("update.html", args=args, current_user=current_user)


@app.route("/update", methods=["POST"])
@login_required
def update_post():
    charger_id = request.args.get("id", type=str)
    firmwareurl = request.form["content"]

    url = f"http://{host_backend}:8080/update"
    json = {"id": charger_id, "firmwareURL": firmwareurl}
    response = requests.post(url, json=json)

    flash("Firmware sent")
    return redirect(f"/update?id={charger_id}")


@app.route("/locallist")
@login_required
def locallist():
    charger_id = request.args.get("id", type=str)
    url = f"http://{host_backend}:8080/locallist"
    response = requests.get(url, json={"id": charger_id})
    json_data = response.json()

    args = {"charger_id": charger_id}

    locallist = json_data["LocalList"]
    return render_template(
        "locallist.html", args=args, locallist=locallist, current_user=current_user
    )


@app.route("/locallist", methods=["POST"])
@login_required
def locallist_post():
    charger_id = request.args.get("id", type=str)
    url = f"http://{host_backend}:8080/locallist"
    response = requests.get(url, json={"id": charger_id})
    json_data = response.json()
    idToken = request.form["content"]
    status = request.form["inputStatus"]
    type = request.form["inputType"]
    args = {"charger_id": charger_id}

    locallist = json_data["LocalList"]
    new_locallist = []
    for element in locallist:
        new_locallist.append(
            {
                "idToken": element["idToken"]["idToken"],
                "type": element["idToken"]["type"],
                "status": element["idTokenInfo"]["status"],
            }
        )

    new_locallist.append(
        {
            "idToken": idToken,
            "type": type,
            "status": status,
        }
    )

    # send new locallist
    url = f"http://{host_backend}:8080/locallist"
    response = requests.post(url, json={"id": charger_id, "locallist": new_locallist})

    return redirect(f"/locallist?id={charger_id}")


@app.route("/deletelocallist")
@login_required
def locallist_delete():
    charger_id = request.args.get("id", type=str)
    id_token = request.args.get("idtoken", type=str)
    # get current locallist
    url = f"http://{host_backend}:8080/locallist"
    response = requests.get(url, json={"id": charger_id})
    json_data = response.json()
    args = {"charger_id": charger_id}

    locallist = json_data["LocalList"]
    new_locallist = []
    for element in locallist:
        if element["idToken"]["idToken"] != id_token:
            new_locallist.append(
                {
                    "idToken": element["idToken"]["idToken"],
                    "type": element["idToken"]["type"],
                    "status": element["idTokenInfo"]["status"],
                }
            )

    # send new locallist
    url = f"http://{host_backend}:8080/locallist"
    response = requests.post(url, json={"id": charger_id, "locallist": new_locallist})

    return redirect(f"/locallist?id={charger_id}")


@app.route("/reserve")
@login_required
def reserve():
    charger_id = request.args.get("id", type=str)

    connector = request.args.get("connector", default="0", type=str)
    args = {"charger_id": charger_id, "connector": connector}
    form = DateForm()
    return render_template(
        "reserve.html", form=form, args=args, current_user=current_user
    )


@app.route("/reserve", methods=["POST"])
@login_required
def reserve_post():
    charger_id = request.args.get("id", type=str)
    connector = request.args.get("connector", default="0", type=int)
    form_date = request.form["dt"]
    form_time = request.form["tp"]
    try:
        date = datetime.strptime(form_date + " " + form_time, "%Y-%m-%d %H:%M")
        if date < datetime.now():
            flash("Please enter a correct date")
            return redirect(url_for("reserve"))
        url = f"http://{host_backend}:8080/reserve"
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
    url = f"http://{host_backend}:8080/displayMessage"
    json = {"id": charger_id}
    response = requests.get(url, json=json)

    url = f"http://{host_backend}:8080/chargers"
    response = requests.get(url)
    json_data = response.json()

    display_messages = json_data[charger_id]["displayMesagges"]
    app.logger.info(display_messages)

    try:
        last_id = len(display_messages)
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
    url = f"http://{host_backend}:8080/variables"
    json = {"id": charger_id}
    response = requests.get(url, json=json)
    json_data = response.json()
    variables = json_data["result"]
    print(variables)
    url = f"http://{host_backend}:8080/chargers"
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


@app.route("/startTransaction")
@login_required
def start_transaction():
    charger_id = request.args.get("id", type=str)

    charger = {"id": charger_id}

    return render_template(
        "authorize.html", charger=charger, current_user=current_user, start=True
    )


@app.route("/startTransaction", methods=["POST"])
@login_required
def start_transaction_post():
    charger_id = request.args.get("id", type=str)

    idToken = request.form["content"]
    type = request.form["inputType"]
    charger = {"id": charger_id}

    url = f"http://{host_backend}:8080/startTransaction"
    json = {"id": charger_id, "idToken": idToken, "idTokenType": type}
    response = requests.post(url, json=json)
    flash("StartTransaction sent")
    return render_template(
        "authorize.html", charger=charger, current_user=current_user, start=False
    )


@app.route("/stopTransaction", methods=["POST"])
@login_required
def stop_transaction_post():
    charger_id = request.args.get("id", type=str)

    transactionId = request.form.get("transactionId", 1)
    charger = {"id": charger_id}

    url = f"http://{host_backend}:8080/stopTransaction"
    json = {"id": charger_id, "transactionId": transactionId}
    if transactionId == 1:
        start = False
    else:
        start = True

    response = requests.post(url, json=json)
    flash("StopTransaction sent")
    return render_template(
        "authorize.html", charger=charger, current_user=current_user, start=start
    )


@app.route("/updatevariable", methods=["GET"])
@login_required
def update_variable():
    charger_id = request.args.get("id", type=str)
    component = request.args.get("component", type=str)
    variable_name = request.args.get("variable", type=str)
    # get variable

    url = f"http://{host_backend}:8080/variables"
    json = {"id": charger_id}
    response = requests.get(url, json=json)
    json_data = response.json()

    variables_dict = json_data["result"]
    old_variable = {
        "component": component,
        "variable": variable_name,
    }

    for variable in variables_dict:
        if (
            variable["component"]["name"] == component
            and variable["variable"]["name"] == variable_name
        ):
            old_variable["value"] = variable["attribute_value"]
            break
    charger = {
        "id": charger_id,
    }
    return render_template(
        "updatevariable.html",
        old_variable=old_variable,
        charger=charger,
        current_user=current_user,
    )


@app.route("/updatevariable", methods=["POST"])
@login_required
def update_variable_post():
    charger_id = request.args.get("id", type=str)
    component = request.args.get("component", type=str)
    variable = request.args.get("variable", type=str)
    value = request.form["content"]
    url = f"http://{host_backend}:8080/variables"

    json = {
        "id": charger_id,
        "component": component,
        "variable": variable,
        "value": value,
    }
    response = requests.post(url, json=json)
    return redirect(f"/variables?id={charger_id}")


@app.route("/displaymessages", methods=["POST"])
@login_required
def display_messages_post():
    charger_id = request.args.get("id", type=str)
    last_id = request.args.get("lastid", type=int)
    msg = request.form["content"]
    url = f"http://{host_backend}:8080/displayMessage"
    json = {"id": charger_id, "msg": msg, "msgId": last_id + 1}
    response = requests.post(url, json=json)
    return redirect(f"/displaymessages?id={charger_id}")


@app.route("/updatedisplaymessage", methods=["GET"])
@login_required
def display_messages_edit():
    charger_id = request.args.get("id", type=str)
    msg_id = request.args.get("msgId", type=int)

    # get old displaymessage

    url = f"http://{host_backend}:8080/displayMessage"
    json = {"id": charger_id}
    response = requests.get(url, json=json)

    url = f"http://{host_backend}:8080/chargers"
    response = requests.get(url)
    json_data = response.json()

    display_messages = json_data[charger_id]["displayMesagges"]

    old_msg = {"id": msg_id, "content": display_messages[msg_id]}
    charger = {
        "id": charger_id,
    }
    return render_template(
        "updatedisplaymessage.html",
        msg=old_msg,
        charger=charger,
        current_user=current_user,
    )


@app.route("/deletedisplaymessage", methods=["GET"])
@login_required
def display_messages_delete():
    charger_id = request.args.get("id", type=str)
    msg_id = request.args.get("msgId", type=int)

    # delete displaymessage

    url = f"http://{host_backend}:8080/displayMessage"
    json = {"id": charger_id, "msgId": msg_id}
    response = requests.delete(url, json=json)

    return redirect(f"/displaymessages?id={charger_id}")


@app.route("/updatedisplaymessage", methods=["POST"])
@login_required
def display_messages_edit_post():
    charger_id = request.args.get("id", type=str)
    msg_id = request.args.get("msgId", type=int)
    msg = request.form["content"]
    url = f"http://{host_backend}:8080/displayMessage"
    json = {"id": charger_id, "msg": msg, "msgId": msg_id + 1}
    response = requests.post(url, json=json)
    return redirect(f"/displaymessages?id={charger_id}")


@app.route("/cancelreservation")
@login_required
def cancel_reserve():
    charger_id = request.args.get("id", default="cp", type=str)
    connector = request.args.get("connector", default="0", type=int)
    json = {"id": charger_id, "connector": int(connector)}
    url = f"http://{host_backend}:8080/cancelReservation"
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
    app.run(debug=True, host="0.0.0.0", port="5000")
