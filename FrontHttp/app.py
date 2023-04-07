from flask import Flask, render_template, request, send_file, redirect
from flask_wtf import Form
from wtforms.fields import DateField
import requests

app = Flask(__name__)


@app.route("/")
def index():
    url = "http://localhost:8080/chargers"
    response = requests.get(url)
    json_data = response.json()
    items = []
    for charger in json_data:
        status = "Free"
        for connector in json_data[charger].get("connectors"):
            if connector == "Reserved":
                status = "Reserved"
        if status == "Reserved":
            color = "bg-danger"
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
    return render_template("home.html", items=items)


@app.route("/charger")
def charger():
    url = "http://localhost:8080/chargers"
    response = requests.get(url)
    json_data = response.json()
    items = []
    status = "Free"
    charger_id = request.args.get("id", default="cp", type=str)
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

    return render_template("home.html", items=items)


class DateForm(Form):
    dt = DateField("DatePicker", format="%Y-%m-%d")


@app.route("/reserve")
def reserve():
    charger_id = request.args.get("id", default="cp", type=str)
    connector = request.args.get("connector", default="0", type=str)
    args = {"charger_id": charger_id, "connector": connector}
    form = DateForm()
    return render_template("reserve.html", form=form, args=args)


@app.route("/cancelreservation")
def cancel_reserve():
    charger_id = request.args.get("id", default="cp", type=str)
    connector = request.args.get("connector", default="0", type=int)
    json = {"id": charger_id, "connector": int(connector)}
    url = "http://localhost:8080/cancelReservation"
    response = requests.post(url, json=json)
    json_data = response.json()
    print(json_data)
    return redirect("/charger", code=302)


@app.route("/reserve", methods=["POST"])
def reserve_post():
    charger_id = request.args.get("id", default="cp", type=str)
    connector = request.args.get("connector", default="0", type=str)
    dateexp = request.form["dt"]
    return f"{dateexp},{charger_id},{connector}", 200


@app.route("/logo.png")
def get_image():
    return send_file("images/logo.png", mimetype="image/png")


@app.route("/favicon.ico")
def get_ico():
    return send_file("images/favicon.ico", mimetype="image/x-icon")


if __name__ == "__main__":
    app.run(debug=True)
