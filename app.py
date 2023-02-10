# py -3 -m venv venv (for mac, 'py -3' = 'python3')
# venv\Scripts\activate (for mac, '. venv/bin/activate')
# pip install Flask
# pip install flask-session
# pip install psycopg2-binary
# pip3 freeze > requirements.txt
# pip install -r requirements.txt

import os
import psycopg2
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
# can delete once postgres is implemented
# import sqlite3
# from sqlite3 import Error
from functools import wraps
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# connection = sqlite3.connect("booklog.db", check_same_thread=False)
# db = connection.cursor()

DATABASE_URL = os.environ['DATABASE_URL']

def getdbconn():
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    return conn


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


def error(code, message):
    return render_template("error.html", code=code, message=message)


@app.after_request
def after_request(response):
    # Ensure responses aren't cached
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    userid = session["user_id"]
    conn = getdbconn()
    db = conn.cursor()
    db.execute("SELECT * FROM hugos")
    hugos = db.fetchall()
    db.execute("SELECT * FROM userdata WHERE userid = %s AND read = 1", (userid,))
    readhugos = list(db.fetchall())
    read = []
    for x in range(len(readhugos)):
        read.append(readhugos[x][1])
    db.execute("SELECT * FROM userdata WHERE userid = %s AND LENGTH(notes) > 0", (userid,))
    hasnotes = list(db.fetchall())
    notes = []
    for x in range(len(hasnotes)):
        notes.append(hasnotes[x][1])
    for x in range(len(hugos)):
        hugos[x] = list(hugos[x])
        if hugos[x][0] in read:
            hugos[x][4] = 1
        else:
            hugos[x][4] = 0
        if hugos[x][0] in notes:
            hugos[x][5] = 1
        else:
            hugos[x][5] = 0
    rewards = ["128301", "127762", "128752", "127776", "129680", "128760", "127756"]
    n = len(readhugos)
    if n != len(hugos):
        if not n % 10:
            n = n / 10
        else:
            n = (n - (n % 10)) / 10
        rewards = rewards[slice(int(n))]
    else:
        rewards = ["128175", "128218", "129299", "128640", "128175"]
    db.close()
    conn.close()
    return render_template("index.html", hugos=hugos, rewards=rewards)


@app.route("/view")
@login_required
def view():
    bookid = request.args.get("id")
    userid = session["user_id"]
    conn = getdbconn()
    db = conn.cursor()
    db.execute("SELECT * FROM hugos WHERE id = %s", (bookid,))
    hugos = db.fetchall()
    db.execute("SELECT * FROM userdata WHERE userid = %s AND bookid = %s", (userid, bookid,))
    user = db.fetchall()
    db.close()
    conn.close()
    return render_template("view.html", bookid=bookid, hugos=hugos, user=user)
        

@app.route("/edit", methods=["GET", "POST"])
@login_required
def edit():
    if request.method == "GET":
        bookid = request.args.get("id")
        userid = session["user_id"]
        conn = getdbconn()
        db = conn.cursor()
        # query db for extant userdata for placeholder info on edit page, pass to template
        db.execute("SELECT * FROM hugos WHERE id = %s", (bookid,))
        result = db.fetchall()
        db.execute("SELECT * FROM userdata WHERE userid = %s AND bookid = %s", (userid, bookid,))
        userdata = db.fetchall()
        db.close()
        conn.close()
        return render_template("edit.html", bookid=bookid, result=result, userdata=userdata)
    else:
        # check userdata where usersid=1 and bookid = %s, if len(check) > 0, don't insert redundant data
        userid = session["user_id"]
        bookid = request.form.get("bookid")
        conn = getdbconn()
        db = conn.cursor()
        db.execute("SELECT * FROM userdata WHERE userid = %s AND bookid = %s", (userid, bookid,))
        result = db.fetchall()
        if len(result) < 1:    
            # insert new userdata rows
            db.execute("INSERT INTO userdata (userid, bookid) VALUES (%s, %s)", (userid, bookid,))
            conn.commit()
        # update new userdata rows with data from request.form.get("input id")
        notes = request.form.get("notes")
        rating = request.form.get("rating")
        read = request.form.get("read")
        if not notes:
            if not rating:
                if not read:
                    db.execute("DELETE FROM userdata WHERE userid = %s AND bookid = %s", (userid, bookid,))
        db.execute("UPDATE userdata SET notes = %s, rating = %s, read = %s WHERE userid = %s AND bookid = %s", (notes, rating, read, userid, bookid))
        conn.commit()
        db.execute("SELECT * FROM userdata WHERE userid = %s AND bookid = %s", (userid, bookid,))
        user = db.fetchall()
        db.execute("SELECT * FROM hugos WHERE id = %s", (bookid,))
        hugos = db.fetchall()
        db.close()
        conn.close()
        return render_template("view.html", bookid=bookid, hugos=hugos, user=user)


@app.route("/register", methods=["GET", "POST"])
def register():
    session.clear()
    if request.method == "POST":
        username = request.form.get("username").upper()
        password = request.form.get("password")
        pwconfirm = request.form.get("pwconfirm")
        if password != pwconfirm:
            return error(400, "Passwords Do Not Match")
        conn = getdbconn()
        db = conn.cursor()
        db.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = db.fetchall()
        if len(user) != 0:
            return error(400, "Username Already Exists")
        hash = generate_password_hash(request.form.get("password"))
        db.execute("INSERT INTO users (username, hash) VALUES (%s, %s)", (username, hash,))
        conn.commit()
        db.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = db.fetchall()
        session["user_id"] = user[0][0]
        session["username"] = user[0][1]
        db.close()
        conn.close()
        return redirect("/")
    else:
        return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()
    if request.method == "POST":
        username = request.form.get("username").upper()
        password = request.form.get("password")
        conn = getdbconn()
        db = conn.cursor()
        db.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = db.fetchall()
        if len(user) != 1:
            return error(403, "Username Not Found")
        if not check_password_hash(user[0][2], password):
            return error(403, "Incorrect Password")
        session["user_id"] = user[0][0]
        session["username"] = user[0][1]
        db.close()
        conn.close()
        return redirect("/")
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")
