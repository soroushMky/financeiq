import os
import json
import pandas as pd
import numpy as np
from datetime import datetime
from dotenv import load_dotenv

from flask import Flask, jsonify, request, send_from_directory
from flask_login import LoginManager, login_required, current_user
from flask_bcrypt import Bcrypt
from flask_cors import CORS

from src.models import db, User, Transaction, Goal, Budget, HealthScore
from src.auth import auth, bcrypt

load_dotenv()

# ── APP SETUP ─────────────────────────────────────────
app = Flask(__name__, static_folder='frontend', static_url_path='')
app.config['SECRET_KEY']                  = os.getenv('FLASK_SECRET_KEY', 'financeiq_secret')
app.config['SQLALCHEMY_DATABASE_URI']     = os.getenv('DATABASE_URL', 'sqlite:///financeiq.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_COOKIE_SECURE']      = True
app.config['SESSION_COOKIE_SAMESITE']    = 'None'
app.config['SESSION_COOKIE_HTTPONLY']    = True

# ── EXTENSIONS ────────────────────────────────────────
db.init_app(app)
bcrypt.init_app(app)
CORS(app,
     supports_credentials=True,
     origins=[
         'https://financeiq-92ut.onrender.com',
         'http://localhost:5173',
         'http://127.0.0.1:5000',
         'http://localhost:5000'
     ],
     allow_headers=['Content-Type'],
     methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])

login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@login_manager.unauthorized_handler
def unauthorized():
    return jsonify({'error': 'Authentication required'}), 401

# ── REGISTER BLUEPRINTS ───────────────────────────────
app.register_blueprint(auth)

# ── CREATE TABLES ─────────────────────────────────────
with app.app_context():
    db.create_all()

# ── SERVE FRONTEND ────────────────────────────────────
@app.route('/')
def index():
    return app.send_static_file('index.html')

# ── HEALTH SCORE CALCULATOR ───────────────────────────
def calculate_health_score(user_id):
    transactions = Transaction.query.filter_by(user_id=user_id).all()
    if not transactions:
        return 50

    amounts   = [t.amount for t in transactions]
    anomalies = [t for t in transactions if t.is_anomaly]
    budgets   = Budget.query.filter_by(user_id=user_id).all()
    goals     = Goal.query.filter_by(user_id=user_id).all()

    # 1 — Spending consistency (0-100)
    if len(amounts) > 1:
        cv = np.std(amounts) / np.mean(amounts)
        spending_consistency = max(0, min(100, int(100 - (cv * 30))))
    else:
        spending_consistency = 50

    # 2 — Anomaly frequency (0-100)
    anomaly_rate  = len(anomalies) / max(len(transactions), 1)
    anomaly_score = max(0, min(100, int(100 - (anomaly_rate * 200))))

    # 3 — Budget adherence (0-100)
    if budgets:
        df = pd.DataFrame([{
            'category': t.category,
            'amount':   t.amount
        } for t in transactions])
        actual_by_cat = df.groupby('category')['amount'].sum()
        adherence_scores = []
        for b in budgets:
            actual = actual_by_cat.get(b.category, 0)
            budget_ann = b.amount * 12
            if budget_ann > 0:
                ratio = actual / budget_ann
                adherence_scores.append(max(0, min(100, int(100 - max(0, ratio - 1) * 100))))
        budget_adherence = int(np.mean(adherence_scores)) if adherence_scores else 50
    else:
        budget_adherence = 50

    # 4 — Goal progress (0-100)
    if goals:
        goal_pcts     = [g.progress_pct for g in goals]
        goal_progress = int(np.mean(goal_pcts))
    else:
        goal_progress = 30

    # 5 — Savings velocity (0-100)
    savings_velocity = min(100, max(0, 60))

    final_score = int(
        spending_consistency * 0.25 +
        anomaly_score        * 0.20 +
        budget_adherence     * 0.25 +
        goal_progress        * 0.15 +
        savings_velocity     * 0.15
    )

    return {
        'score':                final_score,
        'spending_consistency': spending_consistency,
        'anomaly_frequency':    anomaly_score,
        'budget_adherence':     budget_adherence,
        'goal_progress':        goal_progress,
        'savings_velocity':     savings_velocity
    }

# ── ML ANOMALY DETECTION ──────────────────────────────
def detect_anomalies_ml(transactions):
    if len(transactions) < 10:
        return transactions

    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler

    recurring_keywords = [
        'mortgage', 'rent payment', 'insurance',
        'phone company', 'power company', 'internet',
        'city water', 'spotify', 'netflix', 'phone'
    ]

    df = pd.DataFrame([{
        'id':      t.id,
        'amount':  t.amount,
        'month':   t.date.month,
        'day':     t.date.day,
        'weekday': t.date.weekday()
    } for t in transactions])

    features = df[['amount', 'month', 'day', 'weekday']]
    scaler   = StandardScaler()
    scaled   = scaler.fit_transform(features)

    model = IsolationForest(contamination=0.05, random_state=42)
    preds  = model.fit_predict(scaled)
    scores = model.score_samples(scaled)

    for i, t in enumerate(transactions):
        is_recurring = any(kw in t.description.lower() for kw in recurring_keywords)
        t.is_anomaly    = bool(preds[i] == -1) and not is_recurring
        t.anomaly_score = float(abs(scores[i]))

    db.session.commit()
    return transactions

# ── API: UPLOAD CSV ───────────────────────────────────
@app.route('/api/upload', methods=['POST'])
@login_required
def upload_csv():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    if not file.filename.endswith('.csv'):
        return jsonify({'error': 'Please upload a CSV file'}), 400

    try:
        df = pd.read_csv(file)
        df.columns = df.columns.str.strip()

        Transaction.query.filter_by(user_id=current_user.id).delete()

        col_map = {
            'date':        ['Date', 'date', 'DATE'],
            'description': ['Description', 'description', 'Merchant', 'merchant'],
            'amount':      ['Amount', 'amount', 'AMOUNT'],
            'category':    ['Category', 'category'],
            'account':     ['Account Name', 'account', 'Account']
        }

        def find_col(options):
            for o in options:
                if o in df.columns:
                    return o
            return None

        date_col = find_col(col_map['date'])
        desc_col = find_col(col_map['description'])
        amt_col  = find_col(col_map['amount'])
        cat_col  = find_col(col_map['category'])
        acc_col  = find_col(col_map['account'])

        if not date_col or not amt_col:
            return jsonify({'error': 'CSV must have Date and Amount columns'}), 400

        df[date_col] = pd.to_datetime(df[date_col])
        df[amt_col]  = pd.to_numeric(df[amt_col], errors='coerce').abs()
        df = df.dropna(subset=[amt_col])

        if 'Transaction Type' in df.columns:
            df = df[df['Transaction Type'] == 'debit']

        if cat_col:
            non_spending = ['Credit Card Payment', 'Paycheck']
            df = df[~df[cat_col].isin(non_spending)]

        transactions = []
        for _, row in df.iterrows():
            t = Transaction(
                user_id          = current_user.id,
                date             = row[date_col],
                description      = str(row[desc_col]) if desc_col else 'Unknown',
                amount           = float(row[amt_col]),
                category         = str(row[cat_col]) if cat_col else 'Uncategorized',
                account_name     = str(row[acc_col]) if acc_col else 'Unknown',
                transaction_type = 'debit'
            )
            transactions.append(t)

        db.session.bulk_save_objects(transactions)
        db.session.commit()

        saved = Transaction.query.filter_by(user_id=current_user.id).all()
        detect_anomalies_ml(saved)

        score = calculate_health_score(current_user.id)
        current_user.health_score = score['score']
        db.session.commit()

        return jsonify({
            'message':      f'Successfully imported {len(transactions)} transactions',
            'count':        len(transactions),
            'health_score': score
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ── API: SUMMARY ──────────────────────────────────────
@app.route('/api/summary')
@login_required
def summary():
    transactions = Transaction.query.filter_by(user_id=current_user.id).all()
    if not transactions:
        return jsonify({'error': 'No data'}), 404

    amounts   = [t.amount for t in transactions]
    anomalies = [t for t in transactions if t.is_anomaly]

    df = pd.DataFrame([{'date': t.date, 'amount': t.amount} for t in transactions])
    total_amount = df['amount'].sum()
    monthly_avg  = total_amount / 12

    cat_df  = pd.DataFrame([{'category': t.category, 'amount': t.amount} for t in transactions])
    top_cat = cat_df.groupby('category')['amount'].sum().idxmax()
    top_amt = cat_df.groupby('category')['amount'].sum().max()

    health = calculate_health_score(current_user.id)

    return jsonify({
        'total_spent':       round(sum(amounts), 2),
        'monthly_avg':       round(float(monthly_avg), 2),
        'top_category':      top_cat,
        'top_category_amt':  round(float(top_amt), 2),
        'anomaly_count':     len(anomalies),
        'transaction_count': len(transactions),
        'health_score':      health,
        'streak_days':       current_user.streak_days,
        'credit_score':      current_user.credit_score
    })

# ── API: MONTHLY ──────────────────────────────────────
@app.route('/api/monthly')
@login_required
def monthly():
    transactions = Transaction.query.filter_by(user_id=current_user.id).all()
    df = pd.DataFrame([{'date': t.date, 'amount': t.amount} for t in transactions])
    df['month']      = df['date'].dt.month
    df['month_name'] = df['date'].dt.strftime('%B')
    monthly = df.groupby(['month', 'month_name'])['amount'].sum().reset_index()
    monthly = monthly.sort_values('month')
    return jsonify(monthly[['month_name', 'amount']].rename(
        columns={'month_name': 'Month_Name', 'amount': 'Amount'}
    ).to_dict(orient='records'))

# ── API: CATEGORIES ───────────────────────────────────
@app.route('/api/categories')
@login_required
def categories():
    transactions = Transaction.query.filter_by(user_id=current_user.id).all()
    df   = pd.DataFrame([{'category': t.category, 'amount': t.amount} for t in transactions])
    cats = df.groupby('category')['amount'].sum().reset_index()
    cats = cats.sort_values('amount', ascending=False)
    return jsonify(cats.rename(columns={'category': 'Category', 'amount': 'Amount'}).to_dict(orient='records'))

# ── API: BUDGET ───────────────────────────────────────
@app.route('/api/budget')
@login_required
def budget():
    transactions = Transaction.query.filter_by(user_id=current_user.id).all()
    budgets      = Budget.query.filter_by(user_id=current_user.id).all()

    if not budgets:
        return jsonify([])

    df     = pd.DataFrame([{'category': t.category, 'amount': t.amount} for t in transactions])
    actual = df.groupby('category')['amount'].sum().reset_index()
    actual.columns = ['Category', 'Actual']

    result = []
    for b in budgets:
        act = actual[actual['Category'] == b.category]['Actual'].values
        result.append({
            'Category':      b.category,
            'Actual':        round(float(act[0]), 2) if len(act) else 0,
            'Annual_Budget': round(b.amount * 12, 2)
        })

    return jsonify(sorted(result, key=lambda x: x['Actual'], reverse=True)[:8])

# ── API: ANOMALIES ────────────────────────────────────
@app.route('/api/anomalies')
@login_required
def anomalies():
    transactions = Transaction.query.filter_by(
        user_id=current_user.id,
        is_anomaly=True
    ).order_by(Transaction.anomaly_score.desc()).limit(15).all()

    recurring_keywords = [
        'mortgage', 'rent', 'insurance', 'phone company',
        'power company', 'internet', 'city water', 'spotify', 'netflix'
    ]

    df_all  = pd.DataFrame([{
        'category': t.category,
        'amount':   t.amount
    } for t in Transaction.query.filter_by(user_id=current_user.id).all()])
    cat_avg = df_all.groupby('category')['amount'].mean()

    result = []
    for t in transactions:
        is_recurring = any(kw in t.description.lower() for kw in recurring_keywords)
        if is_recurring:
            continue
        avg        = cat_avg.get(t.category, t.amount)
        times_over = round(t.amount / avg, 1) if avg > 0 else 1
        result.append({
            'Date':        t.date.strftime('%b %d, %Y'),
            'Description': t.description,
            'Category':    t.category,
            'Amount':      t.amount,
            'Times_Over':  times_over
        })

    return jsonify(result[:10])

# ── API: TRANSACTIONS ─────────────────────────────────
@app.route('/api/transactions')
@login_required
def transactions():
    txns = Transaction.query.filter_by(
        user_id=current_user.id
    ).order_by(Transaction.date.desc()).limit(20).all()
    return jsonify([t.to_dict() for t in txns])

# ── API: TRANSACTIONS ALL ─────────────────────────────
@app.route('/api/transactions/all')
@login_required
def all_transactions():
    query    = Transaction.query.filter_by(user_id=current_user.id)
    month    = request.args.get('month', 'All')
    category = request.args.get('category', 'All')
    account  = request.args.get('account', 'All')
    search   = request.args.get('search', '').lower()

    if month    != 'All': query = query.filter(db.extract('month', Transaction.date) == datetime.strptime(month, '%B').month)
    if category != 'All': query = query.filter(Transaction.category == category)
    if account  != 'All': query = query.filter(Transaction.account_name == account)

    txns = query.order_by(Transaction.date.desc()).all()

    if search:
        txns = [t for t in txns if search in t.description.lower()]

    return jsonify([t.to_dict() for t in txns])

# ── API: GOALS ────────────────────────────────────────
@app.route('/api/goals', methods=['GET'])
@login_required
def get_goals():
    goals = Goal.query.filter_by(user_id=current_user.id).all()
    return jsonify([g.to_dict() for g in goals])

@app.route('/api/goals', methods=['POST'])
@login_required
def create_goal():
    data = request.get_json()
    goal = Goal(
        user_id      = current_user.id,
        name         = data['name'],
        target_amt   = float(data['target_amt']),
        current_amt  = float(data.get('current_amt', 0)),
        monthly_cont = float(data.get('monthly_cont', 0)),
        deadline     = datetime.strptime(data['deadline'], '%Y-%m') if data.get('deadline') else None,
        emoji        = data.get('emoji', '🎯')
    )
    db.session.add(goal)
    db.session.commit()
    return jsonify(goal.to_dict()), 201

@app.route('/api/goals/<int:goal_id>', methods=['PUT'])
@login_required
def update_goal(goal_id):
    goal = Goal.query.filter_by(id=goal_id, user_id=current_user.id).first_or_404()
    data = request.get_json()
    if 'current_amt'  in data: goal.current_amt  = float(data['current_amt'])
    if 'monthly_cont' in data: goal.monthly_cont = float(data['monthly_cont'])
    if 'name'         in data: goal.name         = data['name']
    db.session.commit()
    return jsonify(goal.to_dict())

@app.route('/api/goals/<int:goal_id>', methods=['DELETE'])
@login_required
def delete_goal(goal_id):
    goal = Goal.query.filter_by(id=goal_id, user_id=current_user.id).first_or_404()
    db.session.delete(goal)
    db.session.commit()
    return jsonify({'message': 'Goal deleted'})

# ── API: BUDGETS ──────────────────────────────────────
@app.route('/api/budgets', methods=['GET'])
@login_required
def get_budgets():
    budgets = Budget.query.filter_by(user_id=current_user.id).all()
    return jsonify([b.to_dict() for b in budgets])

@app.route('/api/budgets', methods=['POST'])
@login_required
def create_budget():
    data   = request.get_json()
    budget = Budget(
        user_id  = current_user.id,
        category = data['category'],
        amount   = float(data['amount'])
    )
    db.session.add(budget)
    db.session.commit()
    return jsonify(budget.to_dict()), 201

# ── API: HEALTH SCORE ─────────────────────────────────
@app.route('/api/health-score')
@login_required
def health_score():
    score = calculate_health_score(current_user.id)
    return jsonify(score)

# ── API: REPORTS ──────────────────────────────────────
@app.route('/api/reports')
@login_required
def reports():
    transactions = Transaction.query.filter_by(user_id=current_user.id).all()
    if not transactions:
        return jsonify({'monthly': [], 'by_account': [], 'top_merchants': []})

    df = pd.DataFrame([{
        'date':        t.date,
        'amount':      t.amount,
        'category':    t.category,
        'account':     t.account_name,
        'description': t.description
    } for t in transactions])

    df['month']      = df['date'].dt.month
    df['month_name'] = df['date'].dt.strftime('%B')

    monthly = df.groupby(['month', 'month_name']).agg(
        total=('amount', 'sum'),
        count=('amount', 'count'),
        avg=('amount', 'mean')
    ).reset_index().sort_values('month')

    by_account    = df.groupby('account')['amount'].sum().reset_index()
    top_merchants = df.groupby('description')['amount'].sum()\
        .reset_index().sort_values('amount', ascending=False).head(10)

    return jsonify({
        'monthly':       monthly[['month_name', 'total', 'count', 'avg']].to_dict(orient='records'),
        'by_account':    by_account.rename(columns={'account': 'account', 'amount': 'total'}).to_dict(orient='records'),
        'top_merchants': top_merchants.rename(columns={'description': 'Description', 'amount': 'Amount'}).to_dict(orient='records')
    })

# ── API: FILTERS ──────────────────────────────────────
@app.route('/api/filters')
@login_required
def filters():
    transactions = Transaction.query.filter_by(user_id=current_user.id).all()
    categories   = sorted(list(set(t.category for t in transactions)))
    accounts     = sorted(list(set(t.account_name for t in transactions)))
    return jsonify({
        'months':     ['All', 'January', 'February', 'March', 'April', 'May', 'June',
                       'July', 'August', 'September', 'October', 'November', 'December'],
        'categories': ['All'] + categories,
        'accounts':   ['All'] + accounts
    })

# ── API: AI COACH ─────────────────────────────────────
@app.route('/api/ai/chat', methods=['POST'])
@login_required
def ai_chat():
    try:
        import anthropic as ant
        data    = request.get_json()
        message = data.get('message', '')

        transactions = Transaction.query.filter_by(user_id=current_user.id).all()
        goals        = Goal.query.filter_by(user_id=current_user.id).all()
        health       = calculate_health_score(current_user.id)

        if transactions:
            df = pd.DataFrame([{
                'category':  t.category,
                'amount':    t.amount,
                'month':     t.date.strftime('%B'),
                'month_num': t.date.month
            } for t in transactions])

            cat_summary    = df.groupby('category')['amount'].sum().round(2).to_dict()
            monthly_totals = df.groupby('month')['amount'].sum().round(2).to_dict()
            total_spent    = sum(t.amount for t in transactions)
            anomaly_cnt    = sum(1 for t in transactions if t.is_anomaly)
        else:
            cat_summary    = {}
            monthly_totals = {}
            total_spent    = 0
            anomaly_cnt    = 0

        context = f"""
You are Nomi, a personal AI financial coach. You are helpful, encouraging, and specific.
Always reference the user's actual data in your responses.

User: {current_user.username}
Financial Health Score: {health['score']}/100
Total Spent: ${total_spent:,.2f}
Anomalies Detected: {anomaly_cnt}
Credit Score: {current_user.credit_score or 'Not set'}
Streak: {current_user.streak_days} days

Monthly Spending Totals:
{json.dumps(monthly_totals, indent=2)}

Spending by Category (Annual):
{json.dumps(cat_summary, indent=2)}

Goals:
{json.dumps([g.to_dict() for g in goals], indent=2)}

Key insights:
- May spending was ${monthly_totals.get('May', 0):,.2f} — significantly above average
- June spending was ${monthly_totals.get('June', 0):,.2f} — significantly above average
- The spike was caused by Mike's Construction Co. home renovation ($17,200 total)
- Average monthly spending excluding May/June is approximately $3,700
- Mortgage & Rent is the largest annual category at $24,754

Be conversational, specific, and actionable. Keep responses under 250 words.
"""

        client   = ant.Anthropic(api_key=os.getenv('CLAUDE_API_KEY'))
        response = client.messages.create(
            model      = 'claude-sonnet-4-6',
            max_tokens = 600,
            system     = context,
            messages   = [{'role': 'user', 'content': message}]
        )

        return jsonify({'response': response.content[0].text})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ── API: LOAD SAMPLE DATA ─────────────────────────────
@app.route('/api/load-sample', methods=['POST'])
@login_required
def load_sample():
    try:
        spending = pd.read_csv('data/spending_clean.csv', parse_dates=['Date'])
        budget   = pd.read_csv('data/Budget.csv')

        Transaction.query.filter_by(user_id=current_user.id).delete()

        transactions = []
        for _, row in spending.iterrows():
            t = Transaction(
                user_id          = current_user.id,
                date             = row['Date'],
                description      = row['Description'],
                amount           = float(row['Amount']),
                category         = row['Category'],
                account_name     = row['Account Name'],
                transaction_type = 'debit'
            )
            transactions.append(t)

        db.session.bulk_save_objects(transactions)

        Budget.query.filter_by(user_id=current_user.id).delete()
        for _, row in budget.iterrows():
            b = Budget(
                user_id  = current_user.id,
                category = row['Category'],
                amount   = float(row['Budget'])
            )
            db.session.add(b)

        db.session.commit()

        saved = Transaction.query.filter_by(user_id=current_user.id).all()
        detect_anomalies_ml(saved)

        score = calculate_health_score(current_user.id)
        current_user.health_score = score['score']
        db.session.commit()

        return jsonify({
            'message':      f'Loaded {len(transactions)} sample transactions',
            'count':        len(transactions),
            'health_score': score
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ── API: SQL INSIGHTS ─────────────────────────────────
@app.route('/api/sql-insights')
@login_required
def sql_insights():
    import sqlalchemy as sa

    results = {}

    # Query 1 — Top 5 merchants by total spend
    q1 = db.session.execute(sa.text("""
        SELECT description,
               ROUND(SUM(amount), 2) as total_spent,
               COUNT(*) as transaction_count
        FROM transactions
        WHERE user_id = :uid AND transaction_type = 'debit'
        GROUP BY description
        ORDER BY total_spent DESC
        LIMIT 5
    """), {'uid': current_user.id})
    results['top_merchants'] = [dict(r._mapping) for r in q1]

    # Query 2 — Monthly spending comparison
    q2 = db.session.execute(sa.text("""
        SELECT strftime('%m', date) as month,
               strftime('%Y', date) as year,
               ROUND(SUM(amount), 2) as total,
               COUNT(*) as txn_count
        FROM transactions
        WHERE user_id = :uid AND transaction_type = 'debit'
        GROUP BY year, month
        ORDER BY year, month
    """), {'uid': current_user.id})
    results['monthly'] = [dict(r._mapping) for r in q2]

    # Query 3 — Category breakdown with percentages
    q3 = db.session.execute(sa.text("""
        SELECT category,
               ROUND(SUM(amount), 2) as total,
               COUNT(*) as txn_count,
               ROUND(SUM(amount) * 100.0 /
                   (SELECT SUM(amount) FROM transactions
                    WHERE user_id = :uid AND transaction_type = 'debit'), 1
               ) as percentage
        FROM transactions
        WHERE user_id = :uid AND transaction_type = 'debit'
        GROUP BY category
        ORDER BY total DESC
    """), {'uid': current_user.id})
    results['categories'] = [dict(r._mapping) for r in q3]

    # Query 4 — Top 5 biggest single transactions
    q4 = db.session.execute(sa.text("""
        SELECT date, description, category,
               ROUND(amount, 2) as amount, account_name
        FROM transactions
        WHERE user_id = :uid AND transaction_type = 'debit'
        ORDER BY amount DESC
        LIMIT 5
    """), {'uid': current_user.id})
    results['biggest'] = [dict(r._mapping) for r in q4]

    # Query 5 — Spending by account
    q5 = db.session.execute(sa.text("""
        SELECT account_name as account,
               ROUND(SUM(amount), 2) as total,
               COUNT(*) as txn_count,
               ROUND(AVG(amount), 2) as avg_amount
        FROM transactions
        WHERE user_id = :uid AND transaction_type = 'debit'
        GROUP BY account_name
        ORDER BY total DESC
    """), {'uid': current_user.id})
    results['by_account'] = [dict(r._mapping) for r in q5]

    return jsonify(results)
@app.route('/api/yearly-comparison')
@login_required
def yearly_comparison():
    year1 = request.args.get('year1', '2018')
    year2 = request.args.get('year2', '2019')

    transactions = Transaction.query.filter_by(user_id=current_user.id).all()
    if not transactions:
        return jsonify({'error': 'No data'}), 404

    df = pd.DataFrame([{
        'date':     t.date,
        'amount':   t.amount,
        'category': t.category,
        'is_anomaly': t.is_anomaly
    } for t in transactions])

    df['year']       = df['date'].dt.year.astype(str)
    df['month']      = df['date'].dt.month
    df['month_name'] = df['date'].dt.strftime('%B')

    results = {}

    for year in [year1, year2]:
        ydf = df[df['year'] == year]
        if ydf.empty:
            results[year] = {
                'total': 0, 'avg': 0, 'anomalies': 0,
                'monthly': [], 'categories': []
            }
            continue

        monthly = ydf.groupby(['month', 'month_name'])['amount'].sum().reset_index()
        monthly = monthly.sort_values('month')

        categories = ydf.groupby('category')['amount'].sum().reset_index()
        categories = categories.sort_values('amount', ascending=False).head(8)

        results[year] = {
            'total':      round(float(ydf['amount'].sum()), 2),
            'avg':        round(float(ydf['amount'].sum() / 12), 2),
            'anomalies':  int(ydf['is_anomaly'].sum()),
            'monthly':    monthly[['month_name', 'amount']].rename(
                columns={'month_name': 'month', 'amount': 'total'}
            ).to_dict(orient='records'),
            'categories': categories.rename(
                columns={'category': 'name', 'amount': 'total'}
            ).to_dict(orient='records')
        }

    return jsonify({
        'year1': year1,
        'year2': year2,
        'data':  results
    })


if __name__ == '__main__':
    app.run(debug=True, port=5000)