from flask import (
    Flask,
    render_template,
    request,
    render_template_string,
    redirect,
    abort,
)
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import sqlite3
import subprocess
import os

app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(basedir, "todos.db")
db = SQLAlchemy(app)


class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(200), nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return "<Task %r>" % self.id


@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")


@app.route("/injection", methods=["GET","POST"])
def injection():
    if len(request.form) > 0:
        artist = request.form["artist"]
        result = get_albums(artist)
        return render_template("injection.html", result=result)
    else:
        return render_template("injection.html", result="")
    


@app.route("/secret", methods=["GET"])
def secret():
    return render_template("secret.html")

@app.route("/login", methods=["GET","POST"])
def login():
    # Login con valores admin admin. Otro usuario válido: Nicholas con contraseña qsrmu
    if request.method == "POST":
        try:
            username = request.form["username"]
            password = request.form["password"]
            message, login = get_user(username, password)
            
            if login:
                return redirect("/secret")
            else:
                print("Hola")
                return render_template("login.html", message=message)
        except:
            return redirect("/")
    else:
        return render_template("login.html")


@app.route("/ssti", methods=["GET"])
def ssti():
    user = request.args.get("user", "")
    # TODO Ejemplo de mostrar todas las variables de entorno {{request.application.__globals__.__builtins__.__import__('os').popen('whoami /all').read()}}
    template = (
        """
   {% extends "layout.html" %}
    {% block content %}
    <p>You are the user """
        + user
        + """</p>
    {% endblock %}"""
    )
    return render_template_string(template)


##SSTI Corregido (para la versión buena)
@app.route("/ssti_filter", methods=["GET"])
def ssti_filter():
    user = request.args.get("user", "")
    bad_chars = "'_#&;"
    if any(char in bad_chars for char in user):
        abort(403)
    template = (
        """
   {% extends "layout.html" %}
    {% block content %}
    <p>You are the user """
        + user
        + """</p>
    {% endblock %}"""
    )
    return render_template_string(template)


@app.route("/ping", methods=["GET", "POST"])
def ping():
    if len(request.form) > 0:
        url = request.form["url"]
        result = ping_host(url)
        return render_template("ping.html", result=result)
    else:
        return render_template("ping.html", result="")


@app.route("/xxs/delete", methods=["POST"])
def xxs_reset():
    try:
        db.session.query(Todo).delete()
        db.session.commit()
    except:
        pass
    return redirect("/xxs")


@app.route("/xxs", methods=["POST", "GET", "PUT"])
def xxs():
    # to fix change {{ task.content|safe }} to {{ task.content }} in xxs.html
    # test with <script>alert("Te falta calle bro")</script>
    if request.method == "POST":
        task_content = request.form["content"]
        new_task = Todo(content=task_content)
        try:
            db.session.add(new_task)
            db.session.commit()
            return redirect("/xxs")
        except:
            return "There was an issue adding your task"
    else:
        tasks = Todo.query.order_by(Todo.date_created).all()
        # tasks = "hola"
        return render_template("xxs.html", tasks=tasks)


def ping_host(url):
    # command injection vul
    try:
        # in windows -c is not needed,4 packets by default
        command = "ping " + url
        data = subprocess.check_output(command, shell=True)
        return data.decode("windows-1252")
    except:
        return f"URL {url} cannot be resolved"


def get_user(username, password):
    try:                
        con = sqlite3.connect("users.db")
        cur = con.cursor()
        cur.execute(
            f"select * from users where username = '{username}' AND password = '{password}'"
        )
        data = cur.fetchall()                
        con.close()
        return [f'Welcome, {data[0][0]}.', True] if len(data) > 0 else ['Incorrect username or password. Please try again.', False]
    except:
        return "Fatal error", False

def get_albums(artist):
    try:                
        con = sqlite3.connect("prosec.db")
        cur = con.cursor()
        cur.execute(
            f"SELECT al.Title FROM albums al INNER JOIN artists ar ON ar.ArtistId = al.ArtistId WHERE ar.Name = '{artist}'"
        )
        data = cur.fetchall()                
        con.close()
        return str(data)
    except:
        return "Fatal error"        


if __name__ == "__main__":
    app.run(debug=True)
