import os
import sqlite3

# Try to import psycopg2 for PostgreSQL support (e.g. Neon DB on Vercel)
HAS_POSTGRES = False
try:
    import psycopg2
    import psycopg2.extras
    HAS_POSTGRES = True
except ImportError:
    HAS_POSTGRES = False

DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_file():
    if os.environ.get('VERCEL') or os.environ.get('AWS_LAMBDA_FUNCTION_NAME'):
        return '/tmp/finance.db'
    base_dir = os.path.dirname(os.path.abspath(__file__))
    try:
        test_file = os.path.join(base_dir, '.write_test')
        with open(test_file, 'w') as f:
            f.write('test')
        os.remove(test_file)
        return os.path.join(base_dir, 'finance.db')
    except Exception:
        return '/tmp/finance.db'

def is_postgres():
    return HAS_POSTGRES and DATABASE_URL and (DATABASE_URL.startswith('postgres://') or DATABASE_URL.startswith('postgresql://'))

def get_connection():
    if is_postgres():
        return psycopg2.connect(DATABASE_URL)
    else:
        db_path = get_db_file()
        need_init = not os.path.exists(db_path)
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        if need_init:
            try:
                _init_db_conn(conn)
            except Exception as e:
                print("Error initializing SQLite schema:", e)
        return conn

def _init_db_conn(conn):
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
            budget REAL DEFAULT 15000.0,
            savings_goal REAL DEFAULT 5000.0,
            FOREIGN KEY (user_email) REFERENCES users (email) ON DELETE CASCADE
        )
    ''')
    demo_email = 'demo@example.com'
    cursor.execute("INSERT OR IGNORE INTO users (email, name, password_hash) VALUES (?, ?, ?)", (demo_email, 'Demo User', 'hash'))
    cursor.execute("INSERT OR IGNORE INTO budgets (user_email, budget) VALUES (?, 15000.0)", (demo_email,))
    conn.commit()

def init_db():
    """Initialize database tables if they do not exist."""
    conn = get_connection()
    cursor = conn.cursor()
    
    if is_postgres():
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS expenses (
                id SERIAL PRIMARY KEY,
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
    else:
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
    
    # Ensure default demo user & budget exist
    demo_email = 'demo@example.com'
    if is_postgres():
        cursor.execute("INSERT INTO users (email, name, password_hash) VALUES (%s, %s, %s) ON CONFLICT (email) DO NOTHING", (demo_email, 'Demo User', 'hash'))
        cursor.execute("INSERT INTO budgets (user_email, budget) VALUES (%s, 15000.0) ON CONFLICT (user_email) DO NOTHING", (demo_email,))
    else:
        cursor.execute("INSERT OR IGNORE INTO users (email, name, password_hash) VALUES (?, ?, ?)", (demo_email, 'Demo User', 'hash'))
        cursor.execute("INSERT OR IGNORE INTO budgets (user_email, budget) VALUES (?, 15000.0)", (demo_email,))

    conn.commit()
    conn.close()

# --- User Management ---

def create_user(name, email, password_hash):
    """Register a new user in database."""
    email = email.lower().strip()
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if is_postgres():
            cursor.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (%s, %s, %s)",
                (name.strip(), email, password_hash)
            )
            cursor.execute(
                "INSERT INTO budgets (user_email, budget) VALUES (%s, 10000.0) ON CONFLICT (user_email) DO NOTHING",
                (email,)
            )
        else:
            cursor.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                (name.strip(), email, password_hash)
            )
            cursor.execute(
                "INSERT OR IGNORE INTO budgets (user_email, budget) VALUES (?, 10000.0)",
                (email,)
            )
        conn.commit()
        conn.close()
        return True, None
    except Exception as e:
        conn.rollback()
        conn.close()
        err_msg = str(e)
        if "UNIQUE" in err_msg.upper() or "already exists" in err_msg.lower():
            return False, "An account with this email already exists."
        return False, f"Registration failed: {err_msg}"

def get_user_by_email(email):
    """Fetch user dict by email."""
    if not email:
        return None
    email = email.lower().strip()
    conn = get_connection()
    if is_postgres():
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
    else:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

# --- Expense Management ---

def add_expense(user_email, amount, description, category, date):
    """Insert a new expense into database."""
    user_email = user_email.lower().strip()
    conn = get_connection()
    cursor = conn.cursor()
    
    # Ensure user row exists to satisfy foreign key constraint
    if is_postgres():
        cursor.execute("INSERT INTO users (email, name, password_hash) VALUES (%s, %s, %s) ON CONFLICT (email) DO NOTHING", (user_email, user_email.split('@')[0], 'hash'))
    else:
        cursor.execute("INSERT OR IGNORE INTO users (email, name, password_hash) VALUES (?, ?, ?)", (user_email, user_email.split('@')[0], 'hash'))

    if is_postgres():
        cursor.execute(
            "INSERT INTO expenses (user_email, amount, description, category, date) VALUES (%s, %s, %s, %s, %s) RETURNING id",
            (user_email, float(amount), description.strip(), category, date)
        )
        expense_id = cursor.fetchone()[0]
    else:
        cursor.execute(
            "INSERT INTO expenses (user_email, amount, description, category, date) VALUES (?, ?, ?, ?, ?)",
            (user_email, float(amount), description.strip(), category, date)
        )
        expense_id = cursor.lastrowid
        
    conn.commit()
    conn.close()
    
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
    conn = get_connection()
    
    if is_postgres():
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute(
            "SELECT id, amount, description, category, date FROM expenses WHERE user_email = %s ORDER BY date DESC, id DESC",
            (user_email,)
        )
    else:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, amount, description, category, date FROM expenses WHERE user_email = ? ORDER BY date DESC, id DESC",
            (user_email,)
        )
        
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def delete_expense(expense_id, user_email):
    """Delete a specific expense owned by user."""
    user_email = user_email.lower().strip()
    conn = get_connection()
    cursor = conn.cursor()
    
    if is_postgres():
        cursor.execute(
            "DELETE FROM expenses WHERE id = %s AND user_email = %s",
            (expense_id, user_email)
        )
    else:
        cursor.execute(
            "DELETE FROM expenses WHERE id = ? AND user_email = ?",
            (expense_id, user_email)
        )
        
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0

# --- Budget Management ---

def get_user_budget(user_email):
    """Get budget for a specific user."""
    if not user_email:
        return 10000.0
    user_email = user_email.lower().strip()
    conn = get_connection()
    
    if is_postgres():
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute("SELECT budget FROM budgets WHERE user_email = %s", (user_email,))
    else:
        cursor = conn.cursor()
        cursor.execute("SELECT budget FROM budgets WHERE user_email = ?", (user_email,))
        
    row = cursor.fetchone()
    if row:
        budget_val = float(row['budget'])
        conn.close()
        return budget_val
    else:
        cursor = conn.cursor()
        if is_postgres():
            cursor.execute("INSERT INTO budgets (user_email, budget) VALUES (%s, 10000.0) ON CONFLICT (user_email) DO NOTHING", (user_email,))
        else:
            cursor.execute("INSERT OR IGNORE INTO budgets (user_email, budget) VALUES (?, 10000.0)", (user_email,))
        conn.commit()
        conn.close()
        return 10000.0

def update_user_budget(user_email, new_budget):
    """Update user's monthly budget."""
    user_email = user_email.lower().strip()
    conn = get_connection()
    cursor = conn.cursor()
    
    if is_postgres():
        cursor.execute(
            "INSERT INTO budgets (user_email, budget) VALUES (%s, %s) ON CONFLICT (user_email) DO UPDATE SET budget = EXCLUDED.budget",
            (user_email, float(new_budget))
        )
    else:
        cursor.execute(
            "INSERT INTO budgets (user_email, budget) VALUES (?, ?) ON CONFLICT(user_email) DO UPDATE SET budget = excluded.budget",
            (user_email, float(new_budget))
        )
        
    conn.commit()
    conn.close()
    return True

if __name__ == '__main__':
    init_db()
    print("Database initialized successfully.")
