from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from .models import db, User
from datetime import datetime

bcrypt = Bcrypt()
auth = Blueprint('auth', __name__)

@auth.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json()

    # Validate input
    if not data.get('email') or not data.get('username') or not data.get('password'):
        return jsonify({'error': 'All fields required'}), 400

    # Check existing user
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already registered'}), 409

    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username already taken'}), 409

    # Create user
    hashed_pw = bcrypt.generate_password_hash(data['password']).decode('utf-8')
    user = User(
        email=data['email'],
        username=data['username'],
        password_hash=hashed_pw
    )

    db.session.add(user)
    db.session.commit()

    login_user(user)

    return jsonify({
        'message': 'Account created successfully',
        'user': {
            'id':       user.id,
            'email':    user.email,
            'username': user.username
        }
    }), 201


@auth.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()

    if not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password required'}), 400

    user = User.query.filter_by(email=data['email']).first()

    if not user or not bcrypt.check_password_hash(user.password_hash, data['password']):
        return jsonify({'error': 'Invalid email or password'}), 401

    login_user(user, remember=True)

    # Update last login + streak
    user.last_login = datetime.utcnow()
    user.streak_days = user.streak_days + 1
    db.session.commit()

    return jsonify({
        'message': 'Login successful',
        'user': {
            'id':           user.id,
            'email':        user.email,
            'username':     user.username,
            'streak_days':  user.streak_days,
            'health_score': user.health_score,
            'credit_score': user.credit_score
        }
    })


@auth.route('/api/auth/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({'message': 'Logged out successfully'})


@auth.route('/api/auth/me', methods=['GET'])
@login_required
def me():
    return jsonify({
        'id':           current_user.id,
        'email':        current_user.email,
        'username':     current_user.username,
        'streak_days':  current_user.streak_days,
        'health_score': current_user.health_score,
        'credit_score': current_user.credit_score,
        'created_at':   current_user.created_at.strftime('%b %d, %Y')
    })


@auth.route('/api/auth/update-credit-score', methods=['POST'])
@login_required
def update_credit_score():
    data = request.get_json()
    score = data.get('score')

    if not score or not (300 <= int(score) <= 900):
        return jsonify({'error': 'Score must be between 300 and 900'}), 400

    current_user.credit_score = int(score)
    db.session.commit()

    return jsonify({
        'message': 'Credit score updated',
        'score':   current_user.credit_score
    })