from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import os
import json
from datetime import datetime


app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this-in-production'

# Configuration
UPLOAD_FOLDER = 'uploads'
RESUME_TEMPLATES_FOLDER = os.path.join(UPLOAD_FOLDER, 'resume_templates')
PORTFOLIO_TEMPLATES_FOLDER = os.path.join(UPLOAD_FOLDER, 'portfolio_templates')
ALLOWED_EXTENSIONS = {'html', 'pdf', 'docx', 'zip', 'css'}
DATA_FILE = 'templates_data.json'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create upload directories
os.makedirs(RESUME_TEMPLATES_FOLDER, exist_ok=True)
os.makedirs(PORTFOLIO_TEMPLATES_FOLDER, exist_ok=True)

# In-memory storage (you can replace this with JSON file storage)
users = {
    'admin': {
        'password_hash': generate_password_hash('admin123'),
        'is_admin': True
    }
}

resume_templates = []
portfolio_templates = []

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def load_data():
    """Load data from JSON file"""
    global resume_templates, portfolio_templates
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r') as f:
                data = json.load(f)
                resume_templates = data.get('resume_templates', [])
                portfolio_templates = data.get('portfolio_templates', [])
    except:
        resume_templates = []
        portfolio_templates = []

def save_data():
    """Save data to JSON file"""
    data = {
        'resume_templates': resume_templates,
        'portfolio_templates': portfolio_templates
    }
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def login_required(f):
    """Decorator to require login"""
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or not session.get('is_admin'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@app.route('/')
def index():
    """Redirect to login page"""
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle admin login"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = users.get(username)
        
        if user and check_password_hash(user['password_hash'], password) and user['is_admin']:
            session['user_id'] = username
            session['username'] = username
            session['is_admin'] = True
            flash('Login successful!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('./template/login.html')

@app.route('/logout')
def logout():
    """Handle logout"""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/admin/template')
@login_required
def admin_dashboard():
    """Admin dashboard with template management"""
    active_resume_templates = [t for t in resume_templates if t.get('is_active', True)]
    active_portfolio_templates = [t for t in portfolio_templates if t.get('is_active', True)]
    
    return render_template('addtemplate.html', 
                         resume_templates=active_resume_templates,
                         portfolio_templates=active_portfolio_templates)

@app.route('/upload_resume_template', methods=['POST'])
@login_required
def upload_resume_template():
    """Handle resume template upload"""
    try:
        name = request.form.get('resume_template_name')
        description = request.form.get('resume_template_description', '')
        category = request.form.get('resume_template_category', 'Professional')
        
        if 'resume_template_file' not in request.files:
            flash('No file selected', 'error')
            return redirect(url_for('admin_dashboard'))
        
        file = request.files['resume_template_file']
        
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(url_for('admin_dashboard'))
        
        if file and allowed_file(file.filename):
            # Generate unique filename
            original_filename = secure_filename(file.filename)
            unique_filename = f"{uuid.uuid4()}_{original_filename}"
            file_path = os.path.join(RESUME_TEMPLATES_FOLDER, unique_filename)
            
            # Save file
            file.save(file_path)
            
            # Create template data
            template_data = {
                'id': len(resume_templates) + 1,
                'name': name,
                'description': description,
                'category': category,
                'file_path': file_path,
                'filename': original_filename,
                'upload_date': datetime.now().isoformat(),
                'is_active': True
            }
            
            resume_templates.append(template_data)
            save_data()
            
            flash('Resume template uploaded successfully!', 'success')
        else:
            flash('Invalid file type. Allowed types: HTML, PDF, DOCX', 'error')
            
    except Exception as e:
        flash(f'Upload failed: {str(e)}', 'error')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/upload_portfolio_template', methods=['POST'])
@login_required
def upload_portfolio_template():
    """Handle portfolio template upload"""
    try:
        name = request.form.get('portfolio_template_name')
        description = request.form.get('portfolio_template_description', '')
        style = request.form.get('portfolio_template_style', 'Modern')
        
        if 'portfolio_template_file' not in request.files:
            flash('No file selected', 'error')
            return redirect(url_for('admin_dashboard'))
        
        file = request.files['portfolio_template_file']
        
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(url_for('admin_dashboard'))
        
        if file and allowed_file(file.filename):
            # Generate unique filename
            original_filename = secure_filename(file.filename)
            unique_filename = f"{uuid.uuid4()}_{original_filename}"
            file_path = os.path.join(PORTFOLIO_TEMPLATES_FOLDER, unique_filename)
            
            # Save file
            file.save(file_path)
            
            # Create template data
            template_data = {
                'id': len(portfolio_templates) + 1,
                'name': name,
                'description': description,
                'style': style,
                'file_path': file_path,
                'filename': original_filename,
                'upload_date': datetime.now().isoformat(),
                'is_active': True
            }
            
            portfolio_templates.append(template_data)
            save_data()
            
            flash('Portfolio template uploaded successfully!', 'success')
        else:
            flash('Invalid file type. Allowed types: HTML, ZIP, CSS', 'error')
            
    except Exception as e:
        flash(f'Upload failed: {str(e)}', 'error')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/preview_template/<template_type>/<int:template_id>')
@login_required
def preview_template(template_type, template_id):
    """Preview a template"""
    template = None
    
    if template_type == 'resume':
        template = next((t for t in resume_templates if t['id'] == template_id), None)
    else:
        template = next((t for t in portfolio_templates if t['id'] == template_id), None)
    
    if template:
        return send_from_directory(
            os.path.dirname(template['file_path']), 
            os.path.basename(template['file_path'])
        )
    else:
        return "Template not found", 404

@app.route('/delete_template/<template_type>/<int:template_id>', methods=['POST'])
@login_required
def delete_template(template_type, template_id):
    """Soft delete a template"""
    if template_type == 'resume':
        for template in resume_templates:
            if template['id'] == template_id:
                template['is_active'] = False
                break
    else:
        for template in portfolio_templates:
            if template['id'] == template_id:
                template['is_active'] = False
                break
    
    save_data()
    flash('Template deleted successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

# API Endpoints for integration
@app.route('/api/resume-templates')
def api_resume_templates():
    """API endpoint for resume templates"""
    active_templates = [
        {
            'id': t['id'],
            'name': t['name'],
            'description': t['description'],
            'category': t['category'],
            'filename': t['filename'],
            'upload_date': t['upload_date']
        }
        for t in resume_templates if t.get('is_active', True)
    ]
    return jsonify(active_templates)

@app.route('/api/portfolio-templates')
def api_portfolio_templates():
    """API endpoint for portfolio templates"""
    active_templates = [
        {
            'id': t['id'],
            'name': t['name'],
            'description': t['description'],
            'style': t['style'],
            'filename': t['filename'],
            'upload_date': t['upload_date']
        }
        for t in portfolio_templates if t.get('is_active', True)
    ]
    return jsonify(active_templates)

@app.route('/api/template/<template_type>/<int:template_id>')
def api_get_template(template_type, template_id):
    """Get specific template data"""
    template = None
    
    if template_type == 'resume':
        template = next((t for t in resume_templates 
                        if t['id'] == template_id and t.get('is_active', True)), None)
    else:
        template = next((t for t in portfolio_templates 
                        if t['id'] == template_id and t.get('is_active', True)), None)
    
    if template:
        return jsonify(template)
    else:
        return jsonify({'error': 'Template not found'}), 404

@app.route('/integrate_template', methods=['POST'])
@login_required
def integrate_template():
    """Handle template integration requests"""
    data = request.get_json()
    template_type = data.get('type')
    template_id = data.get('templateId')
    
    # Store selected template in session for integration
    session[f'selected_{template_type}_template'] = template_id
    
    return jsonify({'status': 'success'})

@app.errorhandler(413)
def too_large(e):
    flash("File is too large. Maximum size is 16MB.", 'error')
    return redirect(url_for('admin_dashboard'))

@app.errorhandler(404)
def not_found(e):
    return "Page not found", 404

@app.errorhandler(500)
def server_error(e):
    return "Internal server error", 500

if __name__ == '__main__':
    # Create upload directories if they don't exist
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(RESUME_TEMPLATES_FOLDER, exist_ok=True)
    os.makedirs(PORTFOLIO_TEMPLATES_FOLDER, exist_ok=True)
    
    # Load existing data
    load_data()
    
    app.run(debug=True, host='0.0.0.0', port=5000)
