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
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'  # Change this to a secure secret key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

CORS(app)  # Enable CORS for all routes
socketio = SocketIO(app, cors_allowed_origins="*")
db = SQLAlchemy(app)

# User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
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
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if not all([username, password]):
        return jsonify({"error": "Missing username or password"}), 400

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid username or password"}), 401

    session['user_id'] = user.id
    return jsonify({"message": "Login successful", "user": {"id": user.id, "username": user.username}})

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
def get_requests():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    requests = Request.query.filter_by(user_id=user_id).order_by(Request.created_at.desc()).all()
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

@app.route('/api/requests/<ref_id>', methods=['GET'])
def get_request(ref_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    req = Request.query.filter_by(ref_id=ref_id, user_id=user_id).first()
    if not req:
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

@app.route('/api/process', methods=['POST'])
def handle_process():
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "Unauthorized"}), 401

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
            user_id=user_id,
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

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    print(f"Starting server at {public_url}")
    socketio.run(app, debug=True, port=5000) 