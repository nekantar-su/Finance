#CS50 Nicholas Kantarellis
import os
from cs50 import SQL
from flask import Flask, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import apology, login_required, lookup, usd

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
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


#@app.after_request
#def after_request(response):
#    """Ensure responses aren't cached"""
#    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
#    response.headers["Expires"] = 0
#    response.headers["Pragma"] = "no-cache"
#    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    trans=db.execute("SELECT symbol,sum(amount)FROM transactions WHERE user_id=? GROUP BY symbol",session["user_id"])
    stock=[]
    cash = db.execute("SELECT cash FROM users WHERE id =?",session["user_id"])[0]["cash"]
    total=0
    for tran in trans:
        quote=lookup(tran["symbol"])
        stock.append({
        "symbol":tran["symbol"],
        "sum":tran["sum(amount)"],
        "name":quote["name"],
        "price":quote["price"],
        "amount":quote["price"] * tran["sum(amount)"]
        })
        total = total+quote["price"] *tran["sum(amount)"]

    total=total+cash
    return render_template("index.html",stock=stock,cash=cash,total=total)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method =="POST":
        stock = request.form.get("symbol")
        amount = request.form.get("shares")
        if amount =="" or lookup(stock) is None:
            return apology("Invalid information")
        try:
            amount=int(amount)
            if amount < 1:
                return apology("share must be a positive integer", 400)
        except ValueError:
            return apology("share must be a positive integer")
        userCash = db.execute("SELECT cash FROM users WHERE id =?",session["user_id"])[0]["cash"]
        price = lookup(stock)["price"]
        if(userCash < price * amount):
            return apology("Not enough funds!")

        db.execute("INSERT INTO transactions(price,amount,symbol,user_id) VALUES(?,?,?,?)",price,amount,stock.upper(),session["user_id"])
        db.execute("UPDATE users SET cash= cash - ? WHERE id = ?",price*amount,session["user_id"])
        return redirect("/")
    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    hist=db.execute("SELECT * FROM transactions WHERE user_id=? ORDER BY date desc",session["user_id"])
    return render_template("history.html",hist=hist)


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


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        stock =lookup(request.form.get("symbol"))
        print(stock)
        if stock=="" or stock==None:
            return apology("ENTER A STOCK")

        return render_template("quoted.html",stock=stock)

    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method=="POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")
        if username == "" or len(db.execute("SELECT username FROM users WHERE username = ?",username))==1:
            return apology("Invalid Username")

        if password=="" or confirmation=="" or password!=confirmation:
            return apology("Invalid Password")

        hPword = generate_password_hash(password);
        db.execute("INSERT INTO users (username,hash) VALUES(?,?)",username,hPword)
        return redirect("/")

    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "POST":
        symbol = request.form.get("symbol")
        amount = request.form.get("shares")
        if amount =="" or symbol=="" :
            return apology("Blank information")
        userShares=db.execute("SELECT sum(amount) FROM transactions WHERE user_id=? AND symbol=?",session["user_id"],symbol)[0]["sum(amount)"]
        amount=int(amount)
        if(amount > userShares and amount>0):
            return apology("NOT ENOUGH FUNDS")
        print(symbol)
        price=lookup(symbol)["price"]
        print(price)
        db.execute("UPDATE users SET cash= cash + ? WHERE id = ?",price*amount,session["user_id"])
        amount=amount-amount*2
        db.execute("INSERT INTO transactions(price,amount,symbol,user_id) VALUES(?,?,?,?)",price,amount,symbol.upper(),session["user_id"])

        return redirect("/")

    available = db.execute("SELECT symbol FROM transactions WHERE user_id = ? AND amount>0 GROUP BY symbol",session["user_id"])
    return render_template("sell.html",available=available)

