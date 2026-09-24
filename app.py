from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from datetime import datetime, timedelta
import json
import os
from collections import defaultdict
import re
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from twilio.twiml.messaging_response import MessagingResponse
import db

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'ai-finance-agent-secret-key-2026')

# Initialize SQLite database schema
db.init_db()


@app.after_request
def set_security_and_cache_headers(response):
    """Global middleware to inject security headers and caching parameters."""
    # Security Headers (Fixes X-Frame-Options, CSP, X-Content-Type-Options, Referrer-Policy, Permissions-Policy)
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=(), payment=()'
    response.headers['Content-Security-Policy'] = "default-src 'self' https: data: 'unsafe-inline' 'unsafe-eval'; frame-ancestors 'self';"

    # Caching & ETag Headers (Fixes Performance & Conditional Request audit findings)
    if request.path.startswith('/static/'):
        response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
    elif response.status_code == 200 and not response.headers.get('Cache-Control'):
        response.headers['Cache-Control'] = 'no-cache, must-revalidate'
    
    return response


# --- SEO & Legal Routes ---

@app.route('/robots.txt')
def robots():
    content = "User-agent: *\nAllow: /\nDisallow: /api/\nSitemap: https://finance-agent-gamma-seven.vercel.app/sitemap.xml\n"
    return content, 200, {'Content-Type': 'text/plain'}


@app.route('/sitemap.xml')
def sitemap():
    domain = "https://finance-agent-gamma-seven.vercel.app"
    pages = [
        {'loc': f'{domain}/', 'priority': '1.0', 'changefreq': 'daily'},
        {'loc': f'{domain}/login', 'priority': '0.8', 'changefreq': 'monthly'},
        {'loc': f'{domain}/signup', 'priority': '0.8', 'changefreq': 'monthly'},
        {'loc': f'{domain}/privacy', 'priority': '0.3', 'changefreq': 'yearly'},
        {'loc': f'{domain}/terms', 'priority': '0.3', 'changefreq': 'yearly'},
        {'loc': f'{domain}/about', 'priority': '0.5', 'changefreq': 'monthly'},
    ]
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for page in pages:
        xml += f'  <url>\n    <loc>{page["loc"]}</loc>\n    <changefreq>{page["changefreq"]}</changefreq>\n    <priority>{page["priority"]}</priority>\n  </url>\n'
    xml += '</urlset>'
    return xml, 200, {'Content-Type': 'application/xml'}


@app.route('/privacy')
def privacy():
    return render_template('privacy.html')


@app.route('/terms')
def terms():
    return render_template('terms.html')


@app.route('/about')
def about():
    return render_template('about.html')


def login_required(f):
    """Decorator to protect routes that require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_email' not in session:
            # If request expects JSON or is an API endpoint, return JSON 401 instead of HTML redirect
            if request.is_json or request.path.startswith('/api/') or request.path in ['/add_expense', '/update_budget', '/get_summary', '/chat']:
                return jsonify({'success': False, 'error': 'Session expired. Please sign in again.', 'redirect': '/login'}), 401
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


class FinanceAgent:
    def __init__(self, user_email):
        self.user_email = user_email.lower().strip() if user_email else 'default_user'
        self.budget = db.get_user_budget(self.user_email)
        self.expenses = db.get_user_expenses(self.user_email)
    
    def categorize_expense(self, description):
        """AI-based expense categorization using keyword matching"""
        description = description.lower()
        
        categories = {
            'food': ['food', 'restaurant', 'cafe', 'lunch', 'dinner', 'breakfast', 'snack', 'zomato', 'swiggy', 'mcdonald', 'burger', 'pizza', 'tea', 'coffee'],
            'transport': ['uber', 'ola', 'bus', 'metro', 'train', 'fuel', 'petrol', 'diesel', 'taxi', 'auto', 'cab', 'flight', 'ticket'],
            'shopping': ['amazon', 'flipkart', 'clothes', 'shopping', 'mall', 'purchase', 'myntra', 'shoes', 'electronics'],
            'entertainment': ['movie', 'netflix', 'spotify', 'game', 'concert', 'party', 'cinema', 'hotstar', 'prime'],
            'utilities': ['electricity', 'water', 'internet', 'phone', 'bill', 'recharge', 'wifi', 'gas'],
            'health': ['medicine', 'doctor', 'hospital', 'pharmacy', 'medical', 'gym', 'health', 'clinic', 'pharmeasy'],
            'education': ['book', 'course', 'tuition', 'fee', 'study', 'college', 'udemy', 'coursera', 'school', 'stationery']
        }
        
        for category, keywords in categories.items():
            if any(keyword in description for keyword in keywords):
                return category
        
        return 'others'
    
    def add_expense(self, amount, description, date=None):
        """Add a new expense to SQLite database"""
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        
        category = self.categorize_expense(description)
        expense = db.add_expense(
            user_email=self.user_email,
            amount=amount,
            description=description,
            category=category,
            date=date
        )
        return expense
    
    def get_spending_summary(self, days=30):
        """Get spending summary for the user"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        total_spent = 0.0
        category_wise = defaultdict(float)
        
        for expense in self.expenses:
            try:
                expense_date = datetime.strptime(expense['date'], '%Y-%m-%d')
                if expense_date >= cutoff_date:
                    amt = float(expense['amount'])
                    total_spent += amt
                    category_wise[expense['category']] += amt
            except ValueError:
                # Handle fallback parsing
                amt = float(expense['amount'])
                total_spent += amt
                category_wise[expense['category']] += amt
        
        current_budget = db.get_user_budget(self.user_email)
        remaining = current_budget - total_spent
        
        return {
            'total_spent': total_spent,
            'by_category': dict(category_wise),
            'budget': current_budget,
            'remaining': remaining,
            'savings_rate': round(((remaining / current_budget) * 100), 1) if current_budget > 0 else 0
        }
    
    def get_ai_insights(self):
        """Generate AI-powered insights and recommendations"""
        summary = self.get_spending_summary()
        insights = []
        
        if summary['budget'] <= 0:
            insights.append({
                'type': 'warning',
                'message': "⚠️ Please set a valid monthly budget to receive spending insights."
            })
            return insights

        spent_percentage = (summary['total_spent'] / summary['budget']) * 100
        
        # Budget utilization alerts
        if spent_percentage > 90:
            insights.append({
                'type': 'warning',
                'message': f"⚠️ Alert! You've spent {spent_percentage:.1f}% of your monthly budget (₹{summary['total_spent']:.2f} / ₹{summary['budget']:.2f}). Time to cut down on non-essential expenses!"
            })
        elif spent_percentage > 75:
            insights.append({
                'type': 'caution',
                'message': f"⚡ Caution! You've used {spent_percentage:.1f}% of your budget. Watch your spending closely!"
            })
        else:
            insights.append({
                'type': 'success',
                'message': f"✅ Great spending management! You've used only {spent_percentage:.1f}% of your monthly budget."
            })
        
        # Category analysis
        if summary['by_category']:
            top_category = max(summary['by_category'], key=summary['by_category'].get)
            top_amount = summary['by_category'][top_category]
            top_pct = (top_amount / summary['total_spent']) * 100 if summary['total_spent'] > 0 else 0
            
            insights.append({
                'type': 'info',
                'message': f"💰 Top Spending Category: '{top_category.title()}' (₹{top_amount:.2f}, {top_pct:.1f}% of total spent)."
            })
        
        # Savings potential
        if summary['remaining'] > 0:
            insights.append({
                'type': 'tip',
                'message': f"💡 Savings Potential: You have ₹{summary['remaining']:.2f} remaining in your budget for this period."
            })
        elif summary['remaining'] < 0:
            insights.append({
                'type': 'warning',
                'message': f"🚨 Over Budget: You have exceeded your budget by ₹{abs(summary['remaining']):.2f}!"
            })
        
        return insights
    
    def chatbot_response(self, user_message):
        """AI chatbot for financial queries"""
        message = user_message.lower()
        summary = self.get_spending_summary()
        
        if any(word in message for word in ['tip', 'advice', 'reduce', 'decrease', 'lower', 'cut down', 'save more']):
            insights = self.get_ai_insights()
            actual_tips = [i['message'] for i in insights if i['type'] in ['info', 'tip', 'warning', 'caution']]
            
            if actual_tips:
                response = "Here are key financial recommendations for you:\n"
                for tip in actual_tips:
                    response += f"• {tip}\n"
                return response.strip()
            return "Keep tracking your expenses regularly and try setting aside 20% of your income into savings!"
            
        elif 'save' in message or 'saving' in message or 'savings' in message:
            if summary['remaining'] > 0:
                return f"Based on your current budget and spending, you can save up to ₹{summary['remaining']:.2f} this month!"
            else:
                return f"You are currently over budget by ₹{abs(summary['remaining']):.2f}. Try reducing spending in your top categories to resume saving."

        elif any(word in message for word in ['spent', 'expenses', 'spending', 'total']):
            return f"You have spent ₹{summary['total_spent']:.2f} out of your ₹{summary['budget']:.2f} monthly budget. Remaining budget: ₹{summary['remaining']:.2f}."
        
        elif 'budget' in message:
            return f"Your current monthly budget is ₹{summary['budget']:.2f}. You can update it anytime from the budget widget on your dashboard."
        
        elif 'category' in message or 'where' in message or 'breakdown' in message:
            if summary['by_category']:
                response = "Your spending breakdown by category:\n"
                for cat, amount in sorted(summary['by_category'].items(), key=lambda x: x[1], reverse=True):
                    pct = (amount / summary['total_spent']) * 100 if summary['total_spent'] > 0 else 0
                    response += f"• {cat.title()}: ₹{amount:.2f} ({pct:.1f}%)\n"
                return response.strip()
            return "No expenses recorded yet. Add an expense to view category breakdowns!"
        
        else:
            return "I am your AI Personal Finance Assistant! You can ask me:\n• 'How much have I spent?'\n• 'Show spending by category'\n• 'Give me a financial tip'\n• 'How much can I save?'"


def parse_sms(sms_text):
    """Parse bank transaction SMS messages"""
    amount_pattern = r'(?:Rs\.?|INR|₹)\s?(\d+(?:,\d+)*(?:\.\d{1,2})?)'
    amount_match = re.search(amount_pattern, sms_text, re.IGNORECASE)

    date_pattern = r'(\d{2}[-/]\d{2}[-/]\d{2,4})'
    date_match = re.search(date_pattern, sms_text)

    merchant_pattern = r'(?:at|to|@)\s+([A-Za-z0-9\s]+?)(?:\s+on|\s+via|\s+ref|\.|\n|$)'
    merchant_match = re.search(merchant_pattern, sms_text, re.IGNORECASE)

    debit_keywords = ['debited', 'spent', 'paid', 'debit', 'withdrawn', 'sent']
    is_debit = any(k in sms_text.lower() for k in debit_keywords)

    if not amount_match or not is_debit:
        return None

    amount_str = amount_match.group(1).replace(',', '')
    description = merchant_match.group(1).strip() if merchant_match else "Bank Transaction"

    date = datetime.now().strftime('%Y-%m-%d')
    if date_match:
        try:
            raw = date_match.group(1).replace('/', '-')
            parts = raw.split('-')
            if len(parts[2]) == 2:
                parts[2] = '20' + parts[2]
            date = f"{parts[2]}-{parts[1]}-{parts[0]}"
        except Exception:
            pass

    return {
        'amount': float(amount_str),
        'description': description,
        'date': date
    }

# --- Authentication Routes ---

@app.route('/')
@login_required
def index():
    user_name = session.get('user_name', 'User')
    user_email = session.get('user_email', '')
    return render_template('index.html', user_name=user_name, user_email=user_email)


@app.route('/signup')
def signup():
    if 'user_email' in session:
        return redirect(url_for('index'))
    return render_template('signup.html')


@app.route('/login')
def login():
    if 'user_email' in session:
        return redirect(url_for('index'))
    return render_template('login.html')


@app.route('/api/signup', methods=['POST'])
def api_signup():
    data = request.json or {}
    name = data.get('name', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not name or not email or not password:
        return jsonify({'success': False, 'error': 'All fields are required.'}), 400

    if len(password) < 6:
        return jsonify({'success': False, 'error': 'Password must be at least 6 characters long.'}), 400

    password_hash = generate_password_hash(password)
    success, error = db.create_user(name, email, password_hash)

    if not success:
        return jsonify({'success': False, 'error': error}), 400

    # Auto-login after successful registration
    session['user_email'] = email
    session['user_name'] = name
    session['user_id'] = email

    return jsonify({'success': True, 'redirect': '/'})


@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({'success': False, 'error': 'Email and password are required.'}), 400

    user = db.get_user_by_email(email)
    if not user or not check_password_hash(user['password_hash'], password):
        return jsonify({'success': False, 'error': 'Invalid email or password.'}), 401

    session['user_email'] = user['email']
    session['user_name'] = user['name']
    session['user_id'] = user['email']

    return jsonify({'success': True, 'redirect': '/'})


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- Dashboard API Endpoints ---

@app.route('/add_expense', methods=['POST'])
@login_required
def add_expense():
    data = request.json or {}
    user_email = session.get('user_email')
    
    if not data.get('amount') or not data.get('description'):
        return jsonify({'success': False, 'error': 'Amount and description are required.'}), 400

    agent = FinanceAgent(user_email)
    expense = agent.add_expense(
        amount=data['amount'],
        description=data['description'],
        date=data.get('date')
    )
    
    return jsonify({'success': True, 'expense': expense})


@app.route('/delete_expense/<int:expense_id>', methods=['POST', 'DELETE'])
@login_required
def delete_expense_route(expense_id):
    user_email = session.get('user_email')
    deleted = db.delete_expense(expense_id, user_email)
    if deleted:
        return jsonify({'success': True, 'message': 'Expense deleted successfully.'})
    return jsonify({'success': False, 'error': 'Expense not found or unauthorized.'}), 404


@app.route('/get_summary')
@login_required
def get_summary():
    user_email = session.get('user_email')
    agent = FinanceAgent(user_email)
    
    summary = agent.get_spending_summary()
    insights = agent.get_ai_insights()
    expenses = db.get_user_expenses(user_email)
    
    return jsonify({
        'summary': summary,
        'insights': insights,
        'expenses': expenses[:20]  # Return recent 20 expenses
    })


@app.route('/chat', methods=['POST'])
@login_required
def chat():
    data = request.json or {}
    user_email = session.get('user_email')
    message = data.get('message', '')
    
    if not message:
        return jsonify({'response': "Please enter a message!"})
        
    agent = FinanceAgent(user_email)
    response = agent.chatbot_response(message)
    
    return jsonify({'response': response})


@app.route('/update_budget', methods=['POST'])
@login_required
def update_budget():
    data = request.json or {}
    user_email = session.get('user_email')
    budget_val = data.get('budget')
    
    if budget_val is None or float(budget_val) < 0:
        return jsonify({'success': False, 'error': 'Invalid budget amount.'}), 400
        
    db.update_user_budget(user_email, float(budget_val))
    return jsonify({'success': True})


@app.route('/sms_webhook', methods=['POST'])
def sms_webhook():
    """Twilio webhook for bank transaction SMS"""
    sms_body = request.form.get('Body', '').strip()
    sender   = request.form.get('From', 'unknown').strip()

    if sender and not sender.startswith('+'):
        sender = '+' + sender

    resp = MessagingResponse()

    if not sms_body:
        resp.message("❌ Empty message received.")
        return str(resp)

    parsed = parse_sms(sms_body)

    if parsed:
        user_email = sender
        agent = FinanceAgent(user_email)
        expense = agent.add_expense(
            amount=parsed['amount'],
            description=parsed['description'],
            date=parsed['date']
        )

        summary = agent.get_spending_summary()

        resp.message(
            f"✅ Expense logged!\n"
            f"💰 ₹{expense['amount']} — {expense['description']}\n"
            f"📂 Category: {expense['category']}\n"
            f"📊 Monthly total: ₹{summary['total_spent']:.2f} / ₹{summary['budget']:.2f}"
        )
    else:
        resp.message(
            "❌ Couldn't read this as a transaction.\n"
            "Make sure it's a debit SMS like:\n"
            "Rs.500 debited from A/c XX1234 at Swiggy"
        )

    return str(resp), 200, {'Content-Type': 'text/xml'}


if __name__ == '__main__':
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        local_ip = '127.0.0.1'
        
    print("\n" + "="*50)
    print(" MOBILE ACCESS LINK AVAILABLE!")
    print(f" Local URL (PC)     : http://127.0.0.1:5001")
    print(f" Mobile Wi-Fi Link  : http://{local_ip}:5001")
    print("="*50 + "\n")
    
    app.run(host='0.0.0.0', port=5001, debug=True)

