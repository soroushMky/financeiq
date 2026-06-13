from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id            = db.Column(db.Integer, primary_key=True)
    email         = db.Column(db.String(120), unique=True, nullable=False)
    username      = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    health_score  = db.Column(db.Integer, default=0)
    credit_score  = db.Column(db.Integer, default=0)
    streak_days   = db.Column(db.Integer, default=0)
    last_login    = db.Column(db.DateTime)

    transactions  = db.relationship('Transaction', backref='user', lazy=True, cascade='all, delete-orphan')
    goals         = db.relationship('Goal', backref='user', lazy=True, cascade='all, delete-orphan')
    budgets       = db.relationship('Budget', backref='user', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<User {self.username}>'


class Transaction(db.Model):
    __tablename__ = 'transactions'

    id               = db.Column(db.Integer, primary_key=True)
    user_id          = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    date             = db.Column(db.DateTime, nullable=False)
    description      = db.Column(db.String(200))
    amount           = db.Column(db.Float, nullable=False)
    category         = db.Column(db.String(100))
    account_name     = db.Column(db.String(100))
    transaction_type = db.Column(db.String(20))
    is_anomaly       = db.Column(db.Boolean, default=False)
    anomaly_score    = db.Column(db.Float, default=0)
    created_at       = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id':          self.id,
            'date':        self.date.strftime('%b %d, %Y'),
            'description': self.description,
            'amount':      self.amount,
            'category':    self.category,
            'account':     self.account_name,
            'is_anomaly':  self.is_anomaly
        }


class Goal(db.Model):
    __tablename__ = 'goals'

    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name         = db.Column(db.String(200), nullable=False)
    target_amt   = db.Column(db.Float, nullable=False)
    current_amt  = db.Column(db.Float, default=0)
    monthly_cont = db.Column(db.Float, default=0)
    deadline     = db.Column(db.DateTime)
    emoji        = db.Column(db.String(10), default='🎯')
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def progress_pct(self):
        if self.target_amt == 0:
            return 0
        return round((self.current_amt / self.target_amt) * 100, 1)

    def to_dict(self):
        return {
            'id':           self.id,
            'name':         self.name,
            'target_amt':   self.target_amt,
            'current_amt':  self.current_amt,
            'monthly_cont': self.monthly_cont,
            'deadline':     self.deadline.strftime('%b %Y') if self.deadline else None,
            'emoji':        self.emoji,
            'progress_pct': self.progress_pct
        }


class Budget(db.Model):
    __tablename__ = 'budgets'

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    category   = db.Column(db.String(100), nullable=False)
    amount     = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id':       self.id,
            'category': self.category,
            'amount':   self.amount
        }


class HealthScore(db.Model):
    __tablename__ = 'health_scores'

    id                   = db.Column(db.Integer, primary_key=True)
    user_id              = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    score                = db.Column(db.Integer, default=0)
    spending_consistency = db.Column(db.Integer, default=0)
    budget_adherence     = db.Column(db.Integer, default=0)
    savings_velocity     = db.Column(db.Integer, default=0)
    goal_progress        = db.Column(db.Integer, default=0)
    anomaly_frequency    = db.Column(db.Integer, default=0)
    recorded_at          = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'score':                self.score,
            'spending_consistency': self.spending_consistency,
            'budget_adherence':     self.budget_adherence,
            'savings_velocity':     self.savings_velocity,
            'goal_progress':        self.goal_progress,
            'anomaly_frequency':    self.anomaly_frequency,
            'recorded_at':          self.recorded_at.strftime('%b %d, %Y')
        }