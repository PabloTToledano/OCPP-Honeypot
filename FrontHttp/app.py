from flask import Flask, render_template

app = Flask(__name__)


@app.route("/")
def index():
    items = [
        {
            "color": "bg-danger",
            "name": "Cargador 1",
            "reverse_status": "Reserved",
            "url": "google.es",
        },
        {
            "color": "bg-success",
            "name": "Cargador 2",
            "reverse_status": "Free",
            "url": "google.es",
        },
        {
            "color": "bg-success",
            "name": "Cargador 3",
            "reverse_status": "Free",
            "url": "google.es",
        },
    ]
    return render_template("home.html", items=items)


if __name__ == "__main__":
    app.run(debug=True)
