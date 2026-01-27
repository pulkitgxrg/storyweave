import sqlite3
from functools import wraps
from flask import Flask, redirect, render_template, request, session, flash, url_for
from flask_session import Session
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config["SECRET_KEY"] = "your-secret-key"
Session(app)

def get_db_connection():
    conn = sqlite3.connect("store.db")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to access this page.", "error")
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session or not session.get("is_admin"):
            flash("Admin access required.", "error")
            return redirect("/")
        return f(*args, **kwargs)
    return decorated_function

@app.route("/")
def index():
    conn = get_db_connection()
    
    categories = conn.execute("SELECT DISTINCT category FROM books ORDER BY category").fetchall()
    
    selected_categories = request.args.getlist("category")
    
    if selected_categories:
        placeholders = ",".join(["?"] * len(selected_categories))
        sql = f"SELECT * FROM books WHERE category IN ({placeholders}) ORDER BY title"
        books = conn.execute(sql, selected_categories).fetchall()
    else:
        books = conn.execute("SELECT * FROM books ORDER BY title LIMIT 12").fetchall()
    
    cart_total = 0
    if session.get("cart"):
        book_ids = [item["id"] for item in session["cart"]]
        if book_ids:
            placeholders = ",".join(["?"] * len(book_ids))
            db_books = conn.execute(f"SELECT * FROM books WHERE id IN ({placeholders})", book_ids).fetchall()
            books_map = {str(b["id"]): b["price"] for b in db_books}
            for item in session["cart"]:
                price = books_map.get(str(item["id"]), 0)
                cart_total += price * item["quantity"]

    conn.close()
    return render_template("index.html", books=books, categories=categories, selected_categories=selected_categories, cart_total=cart_total)

@app.route("/search")
def search():
    query = request.args.get("q", "").strip()
    category = request.args.get("category", "")
    conn = get_db_connection()
    categories = conn.execute("SELECT DISTINCT category FROM books").fetchall()
    
    sql = "SELECT * FROM books WHERE title LIKE ?"
    params = [f"%{query}%"]
    if category:
        sql += " AND category = ?"
        params.append(category)
    
    books = conn.execute(sql, params).fetchall()
    conn.close()
    return render_template("search.html", books=books, categories=categories, query=query)

@app.route("/cart", methods=["GET", "POST"])
def cart():
    if "cart" not in session:
        session["cart"] = []
    
    if request.method == "POST":
        book_id = request.form.get("id")
        quantity = int(request.form.get("quantity", 1))
        
        if quantity < 1:
            flash("Quantity must be at least 1", "error")
            return redirect(url_for("cart"))

        found = False
        for item in session["cart"]:
            if str(item["id"]) == str(book_id):
                item["quantity"] += quantity
                found = True
                break
        
        if not found:
            session["cart"].append({"id": book_id, "quantity": quantity})
        
        session.modified = True
        flash("Item added to cart", "success")
        return redirect("/cart")

    conn = get_db_connection()
    books_in_cart = []
    cart_total = 0
    
    if session["cart"]:
        book_ids = [item["id"] for item in session["cart"]]
        if book_ids:
            placeholders = ",".join(["?"] * len(book_ids))
            db_books = conn.execute(f"SELECT * FROM books WHERE id IN ({placeholders})", book_ids).fetchall()
            
            books_map = {str(b["id"]): b for b in db_books}
            
            valid_cart = []
            for item in session["cart"]:
                book = books_map.get(str(item["id"]))
                if book:
                    item_total = book["price"] * item["quantity"]
                    cart_total += item_total
                    books_in_cart.append({
                        "id": book["id"],
                        "title": book["title"],
                        "author": book["author"],
                        "price": book["price"],
                        "image_url": book["image_url"],
                        "quantity": item["quantity"],
                        "total": item_total
                    })
                    valid_cart.append(item)
            
            if len(valid_cart) != len(session["cart"]):
                session["cart"] = valid_cart
                session.modified = True

    conn.close()
    return render_template("cart.html", books=books_in_cart, cart_total=cart_total)

@app.route("/cart/remove/<book_id>")
def remove_from_cart(book_id):
    session["cart"] = [item for item in session["cart"] if str(item["id"]) != str(book_id)]
    session.modified = True
    flash("Item removed from cart", "success")
    return redirect("/cart")

@app.route("/cart/update", methods=["POST"])
def update_cart():
    for item in session["cart"]:
        quantity = request.form.get(f"quantity_{item['id']}")
        if quantity:
            qty_val = int(quantity)
            if qty_val > 0:
                item["quantity"] = qty_val
            else:
                session["cart"].remove(item)
    session.modified = True
    flash("Cart updated", "success")
    return redirect("/cart")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        if not username or not password:
            flash("Username and password are required", "error")
            return render_template("login.html")

        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["full_name"] = user["full_name"]
            session["is_admin"] = bool(user["is_admin"])
            flash(f"Welcome back, {user['full_name'] or user['username']}!", "success")
            return redirect("/")
        flash("Invalid credentials", "error")
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        if not username or not password:
            flash("Username and password are required", "error")
            return render_template("register.html")

        conn = get_db_connection()
        try:
            conn.execute(
                "INSERT INTO users (username, password, is_admin) VALUES (?, ?, 0)",
                (username, generate_password_hash(password))
            )
            conn.commit()
            flash("Registration successful! Please log in.", "success")
            return redirect("/login")
        except sqlite3.IntegrityError:
            flash("Username already exists", "error")
        except Exception as e:
            flash(f"An error occurred: {e}", "error")
        finally:
            conn.close()
    return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully", "success")
    return redirect("/")

@app.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    if not session.get("cart"):
        flash("Your cart is empty", "error")
        return redirect("/")

    conn = get_db_connection()
    
    cart_items = []
    total_amount = 0
    book_ids = [item["id"] for item in session["cart"]]
    if book_ids:
        placeholders = ",".join(["?"] * len(book_ids))
        db_books = conn.execute(f"SELECT * FROM books WHERE id IN ({placeholders})", book_ids).fetchall()
        books_map = {str(b["id"]): b for b in db_books}
        
        for item in session["cart"]:
            book = books_map.get(str(item["id"]))
            if book:
                item_total = book["price"] * item["quantity"]
                total_amount += item_total
                cart_items.append({
                    "book_id": book["id"],
                    "quantity": item["quantity"],
                    "price": book["price"],
                    "title": book["title"],
                    "author": book["author"],
                    "image_url": book["image_url"]
                })

    if request.method == "POST":
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                "INSERT INTO orders (user_id, total_amount, status) VALUES (?, ?, 'Pending')",
                (session["user_id"], total_amount)
            )
            order_id = cursor.lastrowid
            
            for item in cart_items:
                cursor.execute(
                    "INSERT INTO order_items (order_id, book_id, quantity, price_at_purchase) VALUES (?, ?, ?, ?)",
                    (order_id, item["book_id"], item["quantity"], item["price"])
                )
            
            conn.commit()
            print(f"Order {order_id} created successfully")
            
            session["cart"] = []
            session.modified = True
            flash("Order placed successfully! Thank you for your purchase.", "success")
            return redirect("/profile")
            
        except Exception as e:
            if 'conn' in locals():
                conn.rollback()
            print(f"Checkout error: {e}")
            flash("An error occurred during checkout. Please try again.", "error")
        finally:
            if 'conn' in locals():
                conn.close()

    conn.close()
    return render_template("checkout.html", books=cart_items, total=total_amount)

@app.route("/profile")
@login_required
def profile():
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchone()
    
    orders_db = conn.execute("""
        SELECT o.id, o.total_amount, o.status, o.created_at, COUNT(oi.id) as item_count 
        FROM orders o 
        LEFT JOIN order_items oi ON o.id = oi.order_id 
        WHERE o.user_id = ? 
        GROUP BY o.id 
        ORDER BY o.created_at DESC
    """, (session["user_id"],)).fetchall()
    
    conn.close()
    return render_template("profile.html", user=user, orders=orders_db)

@app.route("/profile/update", methods=["POST"])
@login_required
def update_profile():
    full_name = request.form.get("full_name")
    address = request.form.get("address")
    city = request.form.get("city")
    zip_code = request.form.get("zip_code")
    
    conn = get_db_connection()
    conn.execute("""
        UPDATE users 
        SET full_name = ?, address = ?, city = ?, zip_code = ? 
        WHERE id = ?
    """, (full_name, address, city, zip_code, session["user_id"]))
    conn.commit()
    conn.close()
    
    session["full_name"] = full_name
    flash("Profile updated successfully", "success")
    return redirect("/profile")

@app.route("/admin")
@admin_required
def admin_dashboard():
    conn = get_db_connection()
    books = conn.execute("SELECT * FROM books ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("admin_dashboard.html", books=books)

@app.route("/admin/book/new", methods=["GET", "POST"])
@admin_required
def add_book():
    if request.method == "POST":
        title = request.form["title"]
        author = request.form["author"]
        category = request.form["category"]
        price = float(request.form["price"])
        image_url = request.form["image_url"]
        description = request.form["description"]
        
        conn = get_db_connection()
        conn.execute(
            "INSERT INTO books (title, author, category, price, image_url, description) VALUES (?, ?, ?, ?, ?, ?)",
            (title, author, category, price, image_url, description)
        )
        conn.commit()
        conn.close()
        flash("Book added successfully", "success")
        return redirect(url_for("admin_dashboard"))
    
    return render_template("book_form.html", book=None)

@app.route("/admin/book/edit/<int:book_id>", methods=["GET", "POST"])
@admin_required
def edit_book(book_id):
    conn = get_db_connection()
    if request.method == "POST":
        title = request.form["title"]
        author = request.form["author"]
        category = request.form["category"]
        price = float(request.form["price"])
        image_url = request.form["image_url"]
        description = request.form["description"]
        
        conn.execute(
            "UPDATE books SET title=?, author=?, category=?, price=?, image_url=?, description=? WHERE id=?",
            (title, author, category, price, image_url, description, book_id)
        )
        conn.commit()
        conn.close()
        flash("Book updated successfully", "success")
        return redirect(url_for("admin_dashboard"))
        
    book = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    conn.close()
    return render_template("book_form.html", book=book)

@app.route("/admin/book/delete/<int:book_id>", methods=["POST"])
@admin_required
def delete_book(book_id):
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
        conn.commit()
        flash("Book deleted successfully", "success")
    except sqlite3.IntegrityError:
        flash("Cannot delete book as it belongs to an order.", "error")
    finally:
        conn.close()
    return redirect(url_for("admin_dashboard"))

@app.route("/book/<int:book_id>")
def book_detail(book_id):
    conn = get_db_connection()
    book = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    
    if not book:
        flash("Book not found", "error")
        return redirect("/")
        
    reviews = conn.execute("""
        SELECT r.*, u.username, u.full_name 
        FROM reviews r 
        JOIN users u ON r.user_id = u.id 
        WHERE r.book_id = ? 
        ORDER BY r.created_at DESC
    """, (book_id,)).fetchall()
    
    avg_rating = conn.execute("SELECT AVG(rating) FROM reviews WHERE book_id = ?", (book_id,)).fetchone()[0]
    
    conn.close()
    return render_template("book_detail.html", book=book, reviews=reviews, avg_rating=avg_rating)

@app.route("/book/<int:book_id>/review", methods=["POST"])
@login_required
def add_review(book_id):
    rating = int(request.form.get("rating"))
    comment = request.form.get("comment")
    
    conn = get_db_connection()
    
    # Check if already reviewed? Optional. Let's allow multiple for simplicity unless restricted.
    
    conn.execute(
        "INSERT INTO reviews (user_id, book_id, rating, comment) VALUES (?, ?, ?, ?)",
        (session["user_id"], book_id, rating, comment)
    )
    conn.commit()
    conn.close()
    
    flash("Review submitted successfully!", "success")
    return redirect(url_for('book_detail', book_id=book_id))

if __name__ == "__main__":
    app.run(debug=True, port=5001)