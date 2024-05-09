import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd, distance, location

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///website.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():

    # Load the correct homepage according to the user type
    type = db.execute("SELECT type FROM users WHERE id = ?", session["user_id"])[0]["type"]

    # # Check user type
    # if type == "owner":

    #     # Query to return list of restaurants under user
    #     restaurants = db.execute("SELECT * FROM restaurants WHERE owner_id = ?", session["user_id"])

    #     # Variable to keep track of total critic score
    # if type == "reviewer":

    #     # Query to return reviews made under user
    # else:
    return render_template("index.html", top="Welcome", bottom=type)

@app.route("/like", methods=["POST"])
@login_required
def like():
    type = db.execute("SELECT type FROM users WHERE id = ?", session["user_id"])[0]["type"]
    like = int(request.form.get("like"))
    restaurant_id = request.form.get("restaurant_id")

    if type != "user":
        return apology("must be regular user")
    if not like:
        return apology("don't mess with the values")
    if not (like == 1 or like == -1):
        return apology("don't mess with the values")

    previous = db.execute("SELECT * FROM likes WHERE poster_id = ? and restaurant_id = ?", session["user_id"], restaurant_id)

    if len(previous) > 0:
        if previous[0]["score"] != like:
            db.execute("DELETE FROM likes WHERE poster_id = ? and restaurant_id = ?", session["user_id"], restaurant_id)
            if (like == -1):
                db.execute("UPDATE restaurants SET like = like - 1 WHERE id = ?", restaurant_id)
            else:
                db.execute("UPDATE restaurants SET dislike = dislike - 1 WHERE id = ?", restaurant_id)
        else:
            return apology("already did that")

    try:
        if (like == 1):
            db.execute("UPDATE restaurants SET like = like + 1 WHERE id = ?", restaurant_id)
            flash("Liked")
        else:
            db.execute("UPDATE restaurants SET dislike = dislike + 1 WHERE id = ?", restaurant_id)
            flash("Disliked")
        db.execute("INSERT INTO likes (poster_id, restaurant_id, score) VALUES(?, ?, ?)", session["user_id"], restaurant_id, like)
    except:
         return apology("restaurant doesn't exist")
    return redirect("/restaurant")


@app.route("/reviewlike", methods=["POST"])
@login_required
def reviewlike():
    type = db.execute("SELECT type FROM users WHERE id = ?", session["user_id"])[0]["type"]
    like = int(request.form.get("like"))
    review_id = request.form.get("review_id")

    if type != "user":
        return apology("must be regular user")
    if not like:
        return apology("don't mess with the values")
    if not (like == 1 or like == -1):
        return apology("don't mess with the values")

    previous = db.execute("SELECT * FROM reviewlikes WHERE poster_id = ? and review_id = ?", session["user_id"], review_id)

    if len(previous) > 0:
        if previous[0]["score"] != like:
            db.execute("DELETE FROM reviewlikes WHERE poster_id = ? and review_id = ?", session["user_id"], review_id)
            if (like == -1):
                db.execute("UPDATE reviews SET like = like - 1 WHERE id = ?", review_id)
            else:
                db.execute("UPDATE reviews SET dislike = dislike - 1 WHERE id = ?", review_id)
        else:
            return apology("already did that")

    try:
        if (like == 1):
            db.execute("UPDATE reviews SET like = like + 1 WHERE id = ?", review_id)
            flash("Liked")
        else:
            db.execute("UPDATE reviews SET dislike = dislike + 1 WHERE id = ?", review_id)
            flash("Disliked")
        db.execute("INSERT INTO reviewlikes (poster_id, review_id, score) VALUES(?, ?, ?)", session["user_id"], review_id, like)
    except:
         return apology("review doesn't exist")
    return redirect("/review")


@app.route("/restaurant", methods=["GET", "POST"])
@login_required
def restaurant():
    type = db.execute("SELECT type FROM users WHERE id = ?", session["user_id"])[0]["type"]
    if request.method == "POST":
        name = request.form.get("name")
        # Check the user type
        if type == "owner":

            address = request.form.get("address")
            city = request.form.get("city")
            state = request.form.get("state")
            coordinates = location(address, city, state)

            # Ensures location is submitted
            if not address or not city or not state:
                return apology("must provide location")

            if not coordinates:
                return apology("must provide valid location")

            # Ensures restaurant name is submitted
            if not name:
                return apology("must provide name")

            # Ensures restaurant description is submitted
            if not request.form.get("description"):
                return apology("must provide description")

            # Update database with new restaurant
            db.execute("INSERT INTO restaurants (name, owner_id, description, lat, long, location) VALUES(?, ?, ?, ?, ?, ?)", request.form.get("name"),
                       session["user_id"], request.form.get("description"), coordinates[0], coordinates[1], address + ", " + city + ", " + state)
            flash("Added!")
            return redirect("/")
        else:

            # Ensure restaurant name is inputted
            if not name:
                return apology("must provide restaurant name")
            search_result = db.execute("SELECT * FROM restaurants WHERE name LIKE ?", name)

            # Ensure that search name has restaurant with similar name in database
            if len(search_result) < 1:
                return apology("cannot find restaurant with that name")
            return render_template("restaurant.html", type = type, restaurants = search_result)
    else:
        restaurants = db.execute("SELECT * FROM restaurants")
        return render_template("restaurant.html", type=type, restaurants=restaurants)

@app.route("/review", methods=["GET", "POST"])
@login_required
def review():
    type = db.execute("SELECT type FROM users WHERE id = ?", session["user_id"])[0]["type"]
    if request.method == "POST":
        restaurant_id = request.form.get("restaurant_id")

        # Check the user type
        if type == "reviewer":

            # Ensures restaurant id is submitted
            if not restaurant_id:
                return apology("must provide restaurant id")

            # Ensures score is submitted
            if not request.form.get("score") or (int(request.form.get("score")) < 1 or int(request.form.get("score")) > 5):
                return apology("must provide valid score")

            # Ensures restaurant description is submitted
            if not request.form.get("review"):
                return apology("must provide review")

            # Ensure that restaurant id in database
            if len(db.execute("SELECT * FROM restaurants WHERE id = ?", restaurant_id)) < 1:
                return apology("cannot find restaurant with that id")

            # Ensure that user didn't already post review for restaurant
            if len(db.execute("SELECT * FROM reviews WHERE poster_id = ? AND restaurant_id = ?", session["user_id"], int(restaurant_id))) > 0:
                return apology("already reviewed that restaurant")
            username = db.execute("SELECT username FROM users WHERE id=?", session["user_id"])[0]["username"]

            # Update database with new review
            db.execute("INSERT INTO reviews (poster_id, restaurant_id, review, score, poster_username) VALUES(?, ?, ?, ?, ?)", session["user_id"],
                       restaurant_id, request.form.get("review"), int(request.form.get("score")), username)
            flash("Added!")
            return redirect("/")
        else:
            reviews = db.execute("SELECT * FROM reviews WHERE restaurant_id = ?", restaurant_id)
            try:
                name = db.execute("SELECT * FROM restaurants WHERE id = ?", restaurant_id)[0]["name"]
            except:
                return apology("no reviews for that restaurant")
            return render_template("reviews.html", reviews=reviews, name=name)
    else:
        if type == "owner":
            return render_template("review.html", type=type, restaurants=db.execute("SELECT * FROM restaurants WHERE owner_id = ?", session["user_id"]))
        return render_template("review.html", type=type)


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""

    # Variable to store all previous transactions
    history = db.execute("SELECT symbol, shares, price, date, time FROM purchases WHERE user_id = ?", session["user_id"])

    # Render history.html with all transactions
    return render_template("history.html", history=history)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":

        # Get the username, password, and confirmation values from the form
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")
        type = request.form.get("type")

        # Ensure username was submitted
        if not username:
            return apology("must provide username")

        # Ensure password was submitted
        elif not password:
            return apology("must provide password")

        # Ensure confirmation to password was submitted
        elif not confirmation:
            return apology("must provide confirmation to password")

        # Ensure type was submitted
        elif not type:
            return apology("must provide user type")

        # Ensure confirmation and password match
        elif confirmation != password:
            return apology("confirmation must match password")

        # Ensure type is correct
        elif (type != "reviewer") and (type != "user") and (type != "owner"):
            return apology("must provide valid user type")


        # Will insert new user to database if username is unique (since we have set username to unique index)
        try:
            user = db.execute("INSERT INTO users (username, hash, type) VALUES(?, ?, ?)", username, generate_password_hash(password), type)
        except:
            return apology("username is taken")

        # Remember that this user has logged in
        session["user_id"] = user
        return redirect("/")
    else:
        return render_template("register.html")

@app.route("/password", methods=["GET", "POST"])
def password():
    """Register user"""
    if request.method == "POST":

        # Get the username, password, and confirmation values from the form
        password = request.form.get("password")
        new = request.form.get("new")
        confirmation = request.form.get("confirmation")

        # Ensure username was submitted
        if not new:
            return apology("must provide password")

        # Ensure password was submitted
        elif not new:
            return apology("must provide new password")

        # Ensure confirmation to password was submitted
        elif not confirmation:
            return apology("must provide confirmation to new password")

        # Ensure confirmation and password match
        elif confirmation != new:
            return apology("confirmation must match new password")

        # Ensure user inputs new password
        elif new == password:
            return apology("must provide new password")

        # Compare user password to password inputted
        if check_password_hash(db.execute("SELECT hash FROM users WHERE id = ?", session["user_id"])[0]["hash"], password):
            # Set password to new password if correct password given
            db.execute("UPDATE users SET hash = ? WHERE id = ?", generate_password_hash(new), session["user_id"])
        else:
            return apology("must provide correct password")
        return redirect("/")
    else:
        return render_template("password.html")

