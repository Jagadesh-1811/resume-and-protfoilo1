from flask import Flask, request, jsonify, send_file, session
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import json
import re
import PyPDF2
from docx import Document
from io import BytesIO

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///vitaforge.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'

db = SQLAlchemy(app)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    resumes = db.relationship('Resume', backref='user', lazy=True)
    portfolios = db.relationship('Portfolio', backref='user', lazy=True)

class Resume(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    filename = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=True)
    analysis = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

class Portfolio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    data = db.Column(db.JSON, nullable=False)
    html_content = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

# Create database tables
with app.app_context():
    db.create_all()

# ATS Keywords Database
ATS_KEYWORDS = {
    "technical": [
        {"keyword": "Python", "weight": 5, "category": "Programming", "industry": "tech"},
        {"keyword": "JavaScript", "weight": 5, "category": "Programming", "industry": "tech"},
        # ... (all keywords from frontend)
    ],
    "soft": [
        # ... (all soft skills)
    ],
    # ... other categories
}

# Resume Analysis Functions
def extract_text(file):
    """Extract text from different file formats"""
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    if filename.endswith('.txt'):
        with open(filepath, 'r') as f:
            return f.read()
    
    if filename.endswith('.pdf'):
        with open(filepath, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
            return text
    
    if filename.endswith('.docx'):
        doc = Document(filepath)
        return "\n".join([para.text for para in doc.paragraphs])
    
    return ""

def calculate_keyword_score(content):
    """Calculate keyword match score"""
    score = 0
    max_score = 0
    for category in ATS_KEYWORDS.values():
        for item in category:
            max_score += item["weight"]
            if re.search(r'\b' + re.escape(item["keyword"]) + r'\b', content, re.IGNORECASE):
                score += item["weight"]
    return int((score / max_score) * 100) if max_score > 0 else 0

def calculate_structure_score(content):
    """Calculate resume structure score"""
    # Implementation of structure scoring
    pass

# ... (other analysis functions from frontend JS implemented in Python)

def analyze_resume(content):
    """Perform full resume analysis"""
    analysis = {
        "totalWords": len(content.split()),
        "totalLines": len(content.split('\n')),
        "overallScore": calculate_overall_score(content),
        "keywordScore": calculate_keyword_score(content),
        "structureScore": calculate_structure_score(content),
        # ... other metrics
        "foundKeywords": find_keywords(content),
        "missingKeywords": find_missing_keywords(content),
        "contentIssues": analyze_content(content),
        "recommendations": generate_recommendations(content),
        "originalContent": content
    }
    return analysis

# API Routes
@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    if not data or 'username' not in data or 'email' not in data or 'password' not in data:
        return jsonify({"error": "Missing required fields"}), 400
    
    if User.query.filter_by(username=data['username']).first():
        return jsonify({"error": "Username already exists"}), 400
    
    if User.query.filter_by(email=data['email']).first():
        return jsonify({"error": "Email already registered"}), 400
    
    hashed_password = generate_password_hash(data['password'])
    new_user = User(
        username=data['username'],
        email=data['email'],
        password=hashed_password
    )
    
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({"message": "User created successfully"}), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({"error": "Missing username or password"}), 400
    
    user = User.query.filter_by(username=data['username']).first()
    if not user or not check_password_hash(user.password, data['password']):
        return jsonify({"error": "Invalid credentials"}), 401
    
    session['user_id'] = user.id
    return jsonify({
        "message": "Login successful",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email
        }
    })

@app.route('/api/analyze-resume', methods=['POST'])
def analyze_resume_route():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    try:
        content = extract_text(file)
        analysis = analyze_resume(content)
        
        # Save to database if user is logged in
        if 'user_id' in session:
            new_resume = Resume(
                user_id=session['user_id'],
                filename=secure_filename(file.filename),
                content=content,
                analysis=analysis
            )
            db.session.add(new_resume)
            db.session.commit()
        
        return jsonify(analysis)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/generate-portfolio', methods=['POST'])
def generate_portfolio():
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    try:
        # Generate HTML portfolio from data
        html_content = generate_portfolio_html(data)
        
        # Save to database if user is logged in
        portfolio = None
        if 'user_id' in session:
            portfolio = Portfolio(
                user_id=session['user_id'],
                name=data.get('portfolioName', 'My Portfolio'),
                data=data,
                html_content=html_content
            )
            db.session.add(portfolio)
            db.session.commit()
        
        # Return HTML for download
        return send_file(
            BytesIO(html_content.encode()),
            mimetype='text/html',
            as_attachment=True,
            download_name='portfolio.html'
        )
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/submit-feedback', methods=['POST'])
def submit_feedback():
    data = request.json
    if not data or 'content' not in data:
        return jsonify({"error": "Feedback content required"}), 400
    
    user_id = session.get('user_id')
    new_feedback = Feedback(content=data['content'], user_id=user_id)
    db.session.add(new_feedback)
    db.session.commit()
    
    return jsonify({"message": "Feedback submitted successfully"})

@app.route('/api/user/resumes', methods=['GET'])
def get_user_resumes():
    if 'user_id' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    user = User.query.get(session['user_id'])
    resumes = [{
        "id": r.id,
        "filename": r.filename,
        "created_at": r.created_at.isoformat(),
        "overallScore": r.analysis.get('overallScore', 0) if r.analysis else 0
    } for r in user.resumes]
    
    return jsonify(resumes)

# ... other routes

if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=True)