from flask import Flask, request, jsonify, send_from_directory, session, redirect, url_for
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from download import download_youtube_video
from openai_service import OpenAIService
import subprocess
import os
import sys
import time
import json
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from functools import wraps
import jwt
import uuid
import requests
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

CORS(app)  # Enable CORS for all routes
socketio = SocketIO(app, cors_allowed_origins="*")
db = SQLAlchemy(app)

# JWT token decorator
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(" ")[1]
        if not token:
            print("Token is missing")  # Debug log
            return jsonify({'message': 'Token is missing'}), 401
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = User.query.get(data['user_id'])
            if not current_user:
                print(f"User not found for ID {data['user_id']}")  # Debug log
                return jsonify({'message': 'User not found'}), 401
            print(f"Token validated for user: {current_user.username}")  # Debug log
        except Exception as e:
            print(f"Token validation error: {str(e)}")  # Debug log
            return jsonify({'message': 'Token is invalid'}), 401
        return f(current_user, *args, **kwargs)
    return decorated

# Admin required decorator
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split(" ")[1]
        if not token:
            print("Admin check: Token is missing")  # Debug log
            return jsonify({'message': 'Token is missing'}), 401
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = User.query.get(data['user_id'])
            if not current_user:
                print(f"Admin check: User not found for ID {data['user_id']}")  # Debug log
                return jsonify({'message': 'User not found'}), 401
            if current_user.role != 'admin':
                print(f"Admin check: User {current_user.username} is not an admin")  # Debug log
                return jsonify({'message': 'Admin access required'}), 403
            print(f"Admin check: User {current_user.username} has admin access")  # Debug log
        except Exception as e:
            print(f"Admin check: Token validation error - {str(e)}")  # Debug log
            return jsonify({'message': 'Token is invalid'}), 401
        return f(current_user, *args, **kwargs)
    return decorated

# User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20), default='user')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    requests = db.relationship('Request', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Request model
class Request(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ref_id = db.Column(db.String(20), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    video_url = db.Column(db.String(500), nullable=False)
    operation = db.Column(db.String(50), nullable=False)
    split_option = db.Column(db.Boolean, default=False)
    start_time = db.Column(db.String(20))
    end_time = db.Column(db.String(20))
    status = db.Column(db.String(20), default='pending')
    result = db.Column(db.Text)
    result_url = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Initialize OpenAI service with socketio
openai_service = OpenAIService(socketio)

# Set up Cloudflare Tunnel
try:
    # Check if tunnel exists, if not create one
    tunnel_name = "your-app-name"  # Replace with your desired tunnel name
    try:
        # Try to get existing tunnel
        result = subprocess.run(
            ['cloudflared', 'tunnel', 'list', '--output', 'json'],
            capture_output=True,
            text=True
        )
        tunnels = json.loads(result.stdout)
        tunnel_id = None
        for tunnel in tunnels:
            if tunnel['name'] == tunnel_name:
                tunnel_id = tunnel['id']
                break
        
        if not tunnel_id:
            # Create new tunnel if it doesn't exist
            result = subprocess.run(
                ['cloudflared', 'tunnel', 'create', tunnel_name],
                capture_output=True,
                text=True
            )
            tunnel_id = result.stdout.strip().split(' ')[-1]
        
        # Start the tunnel
        tunnel_process = subprocess.Popen(
            ['cloudflared', 'tunnel', '--url', 'http://localhost:5000', tunnel_id],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait for tunnel to be ready
        time.sleep(5)
        
        # Get the tunnel URL
        result = subprocess.run(
            ['cloudflared', 'tunnel', 'route', 'dns', tunnel_name, f'{tunnel_name}.trycloudflare.com'],
            capture_output=True,
            text=True
        )
        
        public_url = f'https://{tunnel_name}.trycloudflare.com'
        print(f"Public URL: {public_url}")
        
    except Exception as e:
        print(f"Error setting up Cloudflare Tunnel: {str(e)}")
        raise
        
except Exception as e:
    print(f"Error setting up Cloudflare Tunnel: {str(e)}")
    print("Continuing with localhost only...")
    public_url = "http://localhost:5000"

# Authentication routes
@app.route('/api/auth/signup', methods=['POST'])
def signup():
    data = request.json
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if not all([username, email, password]):
        return jsonify({"error": "Missing required fields"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username already exists"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already exists"}), 400

    user = User(username=username, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    return jsonify({"message": "User created successfully"}), 201

@app.route('/api/auth/login', methods=['POST'])
def login():
    try:
        data = request.json
        print(f"Login attempt with data: {data}")  # Debug log
        
        username = data.get('username')
        password = data.get('password')

        if not all([username, password]):
            print("Missing username or password")  # Debug log
            return jsonify({"error": "Missing username or password"}), 400

        user = User.query.filter_by(username=username).first()
        if not user:
            print(f"User not found: {username}")  # Debug log
            return jsonify({"error": "Invalid username or password"}), 401
            
        if not user.check_password(password):
            print(f"Invalid password for user: {username}")  # Debug log
            return jsonify({"error": "Invalid username or password"}), 401

        # Generate JWT token
        token = jwt.encode({
            'user_id': user.id,
            'exp': datetime.utcnow() + timedelta(days=1)
        }, app.config['SECRET_KEY'], algorithm='HS256')

        print(f"Login successful for user: {username}")  # Debug log
        return jsonify({
            "message": "Login successful",
            "user": {
                "id": user.id,
                "username": user.username,
                "role": user.role
            },
            "token": token
        })
    except Exception as e:
        print(f"Login error: {str(e)}")  # Debug log
        return jsonify({"error": "An error occurred during login"}), 500

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    return jsonify({"message": "Logged out successfully"})

@app.route('/api/auth/check', methods=['GET'])
def check_auth():
    user_id = session.get('user_id')
    if user_id:
        user = User.query.get(user_id)
        return jsonify({"authenticated": True, "user": {"id": user.id, "username": user.username}})
    return jsonify({"authenticated": False})

# Protected route example
@app.route('/api/protected')
def protected_route():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    return jsonify({"message": "This is a protected route"})

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/dashboard')
def dashboard():
    return send_from_directory('.', 'dashboard.html')

@app.route('/admin')
def admin():
    return send_from_directory('.', 'admin.html')

def process_video(youtube_url, target_language="en", request_id=None):
    """
    Main function to process YouTube video - downloads, transcribes and translates
    """
    # Download video and extract audio
    audio_path = download_youtube_video(youtube_url)
    if not audio_path:
        return {"error": "Failed to download video"}
        
    # Transcribe and translate
    result = openai_service.transcribe_audio(audio_path, target_language, request_id)
    if not result:
        return {"error": "Failed to transcribe/translate audio"}
        
    return {"translation": result}

# Request routes
@app.route('/api/requests', methods=['GET'])
@token_required
def get_requests(current_user):
    try:
        print(f"Getting requests for user: {current_user.username}")  # Debug log
        requests = Request.query.filter_by(user_id=current_user.id).order_by(Request.created_at.desc()).all()
        print(f"Found {len(requests)} requests")  # Debug log
        
        return jsonify([{
            'id': req.id,
            'ref_id': req.ref_id,
            'video_url': req.video_url,
            'operation': req.operation,
            'split_option': req.split_option,
            'start_time': req.start_time,
            'end_time': req.end_time,
            'status': req.status,
            'created_at': req.created_at.isoformat(),
            'updated_at': req.updated_at.isoformat()
        } for req in requests])
    except Exception as e:
        print(f"Error in get_requests: {str(e)}")  # Debug log
        return jsonify({'message': 'An error occurred while fetching requests'}), 500

@app.route('/api/requests/<ref_id>', methods=['GET'])
@token_required
def get_request(current_user, ref_id):
    try:
        print(f"Getting request {ref_id} for user: {current_user.username}")  # Debug log
        req = Request.query.filter_by(ref_id=ref_id, user_id=current_user.id).first()
        if not req:
            print(f"Request {ref_id} not found")  # Debug log
            return jsonify({"error": "Request not found"}), 404

        return jsonify({
            'id': req.id,
            'ref_id': req.ref_id,
            'video_url': req.video_url,
            'operation': req.operation,
            'split_option': req.split_option,
            'start_time': req.start_time,
            'end_time': req.end_time,
            'status': req.status,
            'result': req.result,
            'created_at': req.created_at.isoformat(),
            'updated_at': req.updated_at.isoformat()
        })
    except Exception as e:
        print(f"Error in get_request: {str(e)}")  # Debug log
        return jsonify({'message': 'An error occurred while fetching request'}), 500

@app.route('/api/process', methods=['POST'])
@token_required
def handle_process(current_user):
    try:
        data = request.json
        youtube_url = data.get('videoUrl')
        operation = data.get('operation')
        split_option = data.get('splitOption', False)
        start_time = data.get('startTime')
        end_time = data.get('endTime')
        request_id = data.get('request_id')
        
        if not youtube_url:
            return jsonify({"error": "Video URL is required"}), 400

        # Create request record
        req = Request(
            ref_id=request_id,
            user_id=current_user.id,
            video_url=youtube_url,
            operation=operation,
            split_option=split_option,
            start_time=start_time,
            end_time=end_time,
            status='pending'
        )
        db.session.add(req)
        db.session.commit()
            
        # Process the video based on operation
        if operation == "translate":
            result = process_video(youtube_url, request_id=request_id)
            if result.get('error'):
                req.status = 'error'
                req.result = result['error']
            else:
                req.status = 'completed'
                req.result = result['translation']
        elif operation == "onlyOst":
            req.status = 'completed'
            req.result = "OST extraction not implemented yet"
        elif operation == "audit":
            req.status = 'completed'
            req.result = "Audit not implemented yet"
        else:
            return jsonify({"error": "Invalid operation"}), 400

        db.session.commit()
        return jsonify({"message": "Request processed successfully", "result": req.result})
        
    except Exception as e:
        if 'req' in locals():
            req.status = 'error'
            req.result = str(e)
            db.session.commit()
        return jsonify({"error": str(e)}), 500

# Admin routes
@app.route('/api/admin/check', methods=['GET'])
@admin_required
def check_admin(current_user):
    print(f"Admin check successful for user: {current_user.username}")  # Debug log
    return jsonify({'message': 'Admin access granted'}), 200

@app.route('/api/admin/users', methods=['GET'])
@token_required
@admin_required
def get_users(current_user):
    try:
        print(f"Getting users list for admin: {current_user.username}")  # Debug log
        users = User.query.all()
        print(f"Found {len(users)} users")  # Debug log
        
        users_list = []
        for user in users:
            try:
                users_list.append({
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'role': user.role,
                    'is_active': user.is_active
                })
            except Exception as e:
                print(f"Error processing user {user.id}: {str(e)}")  # Debug log
                continue
                
        return jsonify(users_list)
    except Exception as e:
        print(f"Error in get_users: {str(e)}")  # Debug log
        return jsonify({'message': 'An error occurred while fetching users'}), 500

@app.route('/api/admin/users', methods=['POST'])
@token_required
@admin_required
def create_user(current_user):
    try:
        if not request.is_json:
            return jsonify({'message': 'Request must be JSON'}), 400

        data = request.get_json()
        print(f"Creating user with data: {data}")  # Debug log
        
        # Validate required fields
        required_fields = ['username', 'email', 'password']
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            return jsonify({'message': f'Missing required fields: {", ".join(missing_fields)}'}), 400
            
        # Check for existing username
        if User.query.filter_by(username=data['username']).first():
            return jsonify({'message': 'Username already exists'}), 400
            
        # Check for existing email
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'message': 'Email already exists'}), 400
        
        # Create new user
        user = User(
            username=data['username'],
            email=data['email'],
            role=data.get('role', 'user')
        )
        user.set_password(data['password'])
        
        try:
            db.session.add(user)
            db.session.commit()
            return jsonify({
                'message': 'User created successfully',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'role': user.role
                }
            }), 201
        except Exception as db_error:
            db.session.rollback()
            return jsonify({'message': 'Database error occurred'}), 500
            
    except Exception as e:
        print(f"Error creating user: {str(e)}")  # Debug log
        return jsonify({'message': 'An error occurred while creating the user'}), 500

@app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
@token_required
@admin_required
def delete_user(current_user, user_id):
    if current_user.id == user_id:
        return jsonify({'message': 'Cannot delete your own account'}), 400
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'message': 'User not found'}), 404
    
    db.session.delete(user)
    db.session.commit()
    
    return jsonify({'message': 'User deleted successfully'}), 200

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    print(f"Starting server at {public_url}")
    socketio.run(app, debug=True, port=5000) 