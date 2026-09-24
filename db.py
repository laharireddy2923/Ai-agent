import sqlite3
import os

if os.environ.get('VERCEL') or os.environ.get('VERCEL_ENV'):
    DB_PATH = '/tmp/finance.db'
else:
    DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'finance.db')

def get_connection():
    # Ensure tables exist even if /tmp is fresh on serverless function cold-start
    if not os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        _create_tables(conn)
        return conn
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def _create_tables(conn):
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            amount REAL NOT NULL,
            description TEXT NOT NULL,
            category TEXT NOT NULL,
            date TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_email) REFERENCES users (email) ON DELETE CASCADE
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS budgets (
            user_email TEXT PRIMARY KEY,
            budget REAL DEFAULT 10000.0,
            savings_goal REAL DEFAULT 5000.0,
            FOREIGN KEY (user_email) REFERENCES users (email) ON DELETE CASCADE
        )
    ''')
    conn.commit()

def init_db():
    """Initialize database tables if they do not exist."""
    with get_connection() as conn:
        _create_tables(conn)

# --- User Management ---

def create_user(name, email, password_hash):
    """Register a new user in database."""
    email = email.lower().strip()
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                (name.strip(), email, password_hash)
            )
            # Default budget for new user
            cursor.execute(
                "INSERT OR IGNORE INTO budgets (user_email, budget) VALUES (?, 10000.0)",
                (email,)
            )
            conn.commit()
            return True, None
        except sqlite3.IntegrityError:
            return False, "An account with this email already exists."

def get_user_by_email(email):
    """Fetch user dict by email."""
    if not email:
        return None
    email = email.lower().strip()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        row = cursor.fetchone()
        return dict(row) if row else None

# --- Expense Management ---

def add_expense(user_email, amount, description, category, date):
    """Insert a new expense into database."""
    user_email = user_email.lower().strip()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO expenses (user_email, amount, description, category, date) VALUES (?, ?, ?, ?, ?)",
            (user_email, float(amount), description.strip(), category, date)
        )
        expense_id = cursor.lastrowid
        conn.commit()
        return {
            'id': expense_id,
            'user_email': user_email,
            'amount': float(amount),
            'description': description.strip(),
            'category': category,
            'date': date
        }

def get_user_expenses(user_email):
    """Retrieve all expenses for a given user."""
    if not user_email:
        return []
    user_email = user_email.lower().strip()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, amount, description, category, date FROM expenses WHERE user_email = ? ORDER BY date DESC, id DESC",
            (user_email,)
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def delete_expense(expense_id, user_email):
    """Delete a specific expense owned by user."""
    user_email = user_email.lower().strip()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM expenses WHERE id = ? AND user_email = ?",
            (expense_id, user_email)
        )
        affected = cursor.rowcount
        conn.commit()
        return affected > 0

# --- Budget Management ---

def get_user_budget(user_email):
    """Get budget for a specific user."""
    if not user_email:
        return 10000.0
    user_email = user_email.lower().strip()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT budget FROM budgets WHERE user_email = ?", (user_email,))
        row = cursor.fetchone()
        if row:
            return float(row['budget'])
        else:
            cursor.execute("INSERT OR IGNORE INTO budgets (user_email, budget) VALUES (?, 10000.0)", (user_email,))
            conn.commit()
            return 10000.0

def update_user_budget(user_email, new_budget):
    """Update user's monthly budget."""
    user_email = user_email.lower().strip()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO budgets (user_email, budget) VALUES (?, ?) ON CONFLICT(user_email) DO UPDATE SET budget = excluded.budget",
            (user_email, float(new_budget))
        )
        conn.commit()
        return True

if __name__ == '__main__':
    init_db()
    print("Database initialized successfully.")
