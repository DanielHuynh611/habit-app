import re
import uuid
from datetime import datetime, timedelta
from functools import wraps

import jwt
from flask import Blueprint, request, jsonify, current_app
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash

account_creation_bp = Blueprint('account_creation', __name__)

JWT_SECRET_KEY = 'your-secret-key-change-in-production'
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_DAYS = 30


def get_db():
    """Get database connection from Flask app context"""
    if not hasattr(current_app, 'db_engine'):
        raise RuntimeError("Database engine not configured")
    return current_app.db_engine.connect()


def validate_email(email):
    """Validate email format"""
    if not email or len(email) < 3 or len(email) > 255:
        return False
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(email_regex, email) is not None


def validate_password(password):
    """Validate password meets minimum requirements"""
    if not password or len(password) < 8 or len(password) > 128:
        return False
    return True


def generate_token(user_id, email):
    """Generate JWT token for user authentication"""
    payload = {
        'user_id': user_id,
        'email': email,
        'exp': datetime.utcnow() + timedelta(days=JWT_EXPIRATION_DAYS),
        'iat': datetime.utcnow()
    }
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token


def decode_token(token):
    """Decode and validate JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def require_auth(f):
    """Decorator to require authentication for protected routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            return jsonify({
                'error': 'MISSING_TOKEN',
                'message': 'Authentication token is required'
            }), 401
        
        # Extract token from "Bearer <token>" format
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            return jsonify({
                'error': 'INVALID_TOKEN',
                'message': 'Authentication token is invalid or expired'
            }), 401
        
        token = parts[1]
        payload = decode_token(token)
        
        if not payload:
            return jsonify({
                'error': 'INVALID_TOKEN',
                'message': 'Authentication token is invalid or expired'
            }), 401
        
        # Attach user info to request context
        request.user_id = payload.get('user_id')
        request.user_email = payload.get('email')
        
        return f(*args, **kwargs)
    
    return decorated_function


@account_creation_bp.route('/api/auth/signup', methods=['POST'])
def sign_up():
    """Creates a new user account with email and password, returns authentication token for automatic login"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'error': 'INVALID_EMAIL',
                'message': 'Email address is invalid'
            }), 400
        
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        
        # Validate email
        if not validate_email(email):
            return jsonify({
                'error': 'INVALID_EMAIL',
                'message': 'Email address is invalid'
            }), 400
        
        # Validate password
        if not validate_password(password):
            return jsonify({
                'error': 'INVALID_PASSWORD',
                'message': 'Password must be at least 8 characters'
            }), 400
        
        # Generate user ID and hash password
        user_id = str(uuid.uuid4())
        password_hash = generate_password_hash(password)
        now = datetime.utcnow()
        
        # Insert user into database
        conn = get_db()
        try:
            # Check if email already exists
            check_query = text("SELECT id FROM users WHERE email = :email")
            result = conn.execute(check_query, {'email': email})
            existing_user = result.fetchone()
            
            if existing_user:
                return jsonify({
                    'error': 'EMAIL_EXISTS',
                    'message': 'An account with this email already exists'
                }), 409
            
            # Insert new user
            insert_query = text("""
                INSERT INTO users (id, email, password_hash, created_at, updated_at)
                VALUES (:id, :email, :password_hash, :created_at, :updated_at)
            """)
            
            conn.execute(insert_query, {
                'id': user_id,
                'email': email,
                'password_hash': password_hash,
                'created_at': now,
                'updated_at': now
            })
            conn.commit()
            
        except IntegrityError:
            conn.rollback()
            return jsonify({
                'error': 'EMAIL_EXISTS',
                'message': 'An account with this email already exists'
            }), 409
        except Exception as e:
            conn.rollback()
            return jsonify({
                'error': 'INTERNAL_ERROR',
                'message': 'Failed to create account'
            }), 500
        finally:
            conn.close()
        
        # Generate authentication token
        token = generate_token(user_id, email)
        
        return jsonify({
            'user_id': user_id,
            'email': email,
            'token': token
        }), 201
        
    except Exception as e:
        return jsonify({
            'error': 'INTERNAL_ERROR',
            'message': 'Failed to create account'
        }), 500


@account_creation_bp.route('/api/auth/login', methods=['POST'])
def log_in():
    """Authenticates existing user with email and password, returns authentication token for session"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'error': 'MISSING_FIELDS',
                'message': 'Email and password are required'
            }), 400
        
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        
        # Check required fields
        if not email or not password:
            return jsonify({
                'error': 'MISSING_FIELDS',
                'message': 'Email and password are required'
            }), 400
        
        # Query user from database
        conn = get_db()
        try:
            query = text("SELECT id, email, password_hash FROM users WHERE email = :email")
            result = conn.execute(query, {'email': email})
            user = result.fetchone()
            
            if not user:
                return jsonify({
                    'error': 'INVALID_CREDENTIALS',
                    'message': 'Email or password is incorrect'
                }), 401
            
            # Verify password
            if not check_password_hash(user.password_hash, password):
                return jsonify({
                    'error': 'INVALID_CREDENTIALS',
                    'message': 'Email or password is incorrect'
                }), 401
            
            # Generate authentication token
            token = generate_token(user.id, user.email)
            
            return jsonify({
                'user_id': user.id,
                'email': user.email,
                'token': token
            }), 200
            
        except Exception as e:
            return jsonify({
                'error': 'INTERNAL_ERROR',
                'message': 'Failed to authenticate'
            }), 500
        finally:
            conn.close()
            
    except Exception as e:
        return jsonify({
            'error': 'INTERNAL_ERROR',
            'message': 'Failed to authenticate'
        }), 500


@account_creation_bp.route('/api/auth/verify', methods=['GET'])
@require_auth
def verify_session():
    """Validates authentication token and returns current user information to maintain session across page loads"""
    try:
        user_id = request.user_id
        
        # Query user from database to ensure they still exist
        conn = get_db()
        try:
            query = text("SELECT id, email FROM users WHERE id = :id")
            result = conn.execute(query, {'id': user_id})
            user = result.fetchone()
            
            if not user:
                return jsonify({
                    'error': 'USER_NOT_FOUND',
                    'message': 'User account no longer exists'
                }), 404
            
            return jsonify({
                'user_id': user.id,
                'email': user.email
            }), 200
            
        except Exception as e:
            return jsonify({
                'error': 'INTERNAL_ERROR',
                'message': 'Failed to verify session'
            }), 500
        finally:
            conn.close()
            
    except Exception as e:
        return jsonify({
            'error': 'INTERNAL_ERROR',
            'message': 'Failed to verify session'
        }), 500
