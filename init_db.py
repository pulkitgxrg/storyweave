import sqlite3
from werkzeug.security import generate_password_hash

conn = sqlite3.connect("store.db")
cursor = conn.cursor()

cursor.execute("PRAGMA foreign_keys = ON")

cursor.executescript("""
DROP TABLE IF EXISTS reviews;
DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS books;
DROP TABLE IF EXISTS users;
""")

cursor.execute("""
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    is_admin BOOLEAN NOT NULL DEFAULT 0,
    full_name TEXT,
    address TEXT,
    city TEXT,
    zip_code TEXT
)
""")

cursor.execute("""
CREATE TABLE books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    category TEXT NOT NULL,
    price REAL NOT NULL,
    image_url TEXT NOT NULL,
    description TEXT
)
""")

cursor.execute("""
CREATE TABLE reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    book_id INTEGER NOT NULL,
    rating INTEGER NOT NULL,
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id),
    FOREIGN KEY (book_id) REFERENCES books (id)
)
""")

cursor.execute("""
CREATE TABLE orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    total_amount REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'Pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
)
""")

cursor.execute("""
CREATE TABLE order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    book_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    price_at_purchase REAL NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders (id),
    FOREIGN KEY (book_id) REFERENCES books (id)
)
""")

admin_pass = generate_password_hash("admin123")
cursor.execute("INSERT INTO users (username, password, is_admin, full_name) VALUES (?, ?, ?, ?)", ("admin", admin_pass, 1, "Admin User"))
user_pass = generate_password_hash("password")
cursor.execute("INSERT INTO users (username, password, is_admin, full_name) VALUES (?, ?, ?, ?)", ("user", user_pass, 0, "Demo User"))

books = [
    ('The Great Gatsby', 'F. Scott Fitzgerald', 'Fiction', 9.99, 'https://upload.wikimedia.org/wikipedia/commons/7/7a/The_Great_Gatsby_Cover_1925_Retouched.jpg', 'A classic novel about the American Dream'),
    ('1984', 'George Orwell', 'Fiction', 12.99, 'https://m.media-amazon.com/images/I/81+LDW4qePL._UF1000,1000_QL80_.jpg', 'A dystopian novel about surveillance and control'),
    ('Clean Code', 'Robert C. Martin', 'Technology', 39.99, 'https://images-na.ssl-images-amazon.com/images/I/41jEbK-jG+L._SX376_BO1,204,203,200_.jpg', 'A handbook of software craftsmanship'),
    ('The Pragmatic Programmer', 'Andy Hunt & Dave Thomas', 'Technology', 45.99, 'https://m.media-amazon.com/images/I/51W1sBPO7tL._SX380_BO1,204,203,200_.jpg', 'Your journey to mastery'),
    ('To Kill a Mockingbird', 'Harper Lee', 'Fiction', 11.50, 'https://upload.wikimedia.org/wikipedia/commons/4/4f/To_Kill_a_Mockingbird_%28first_edition_cover%29.jpg', 'A novel about racial injustice in the Deep South'),
    ('The Hobbit', 'J.R.R. Tolkien', 'Fantasy', 15.00, 'https://m.media-amazon.com/images/I/710+HcoP38L._AC_UF1000,1000_QL80_.jpg', 'A fantasy novel about the journey of Bilbo Baggins')
]

cursor.executemany("""
INSERT INTO books (title, author, category, price, image_url, description) 
VALUES (?, ?, ?, ?, ?, ?)
""", books)

conn.commit()
conn.close()
print("Database initialized successfully.")