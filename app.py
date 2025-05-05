import os
import json
import secrets
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, abort
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# Initialize Flask app
app = Flask(__name__)

# =============================================================================
# CONFIGURATION (Use environment variables in production)
# =============================================================================

# Security Configuration
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))  # Change in production!
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour session lifetime
app.config['SESSION_COOKIE_SECURE'] = True  # Only send cookies over HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# File Upload Configuration
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB limit
app.config['ALLOWED_EXTENSIONS'] = {'pdf'}

# Database Files
app.config['QUEUE_FILE'] = 'data/file_queue.json'
app.config['USERS_FILE'] = 'data/users.json'
app.config['CONFIG_FILE'] = 'data/config.json'

# Admin Configuration
app.config['ADMIN_EMAIL'] = os.environ.get('ADMIN_EMAIL', 'admin@mjcems.com')
app.config['MAX_LOGIN_ATTEMPTS'] = 5
app.config['LOCKOUT_TIME'] = 300  # 5 minutes

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def initialize_files():
    """Create required directories and files if they don't exist"""
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs('data', exist_ok=True)
    
    # Initialize queue file
    if not os.path.exists(app.config['QUEUE_FILE']):
        with open(app.config['QUEUE_FILE'], 'w') as f:
            json.dump([], f)
    
    # Initialize users file with admin if empty
    if not os.path.exists(app.config['USERS_FILE']):
        with open(app.config['USERS_FILE'], 'w') as f:
            default_password = generate_password_hash('admin123')
            json.dump({
                'admin': {
                    'password': default_password,
                    'email': app.config['ADMIN_EMAIL'],
                    'role': 'admin',
                    'created_at': datetime.now().isoformat()
                }
            }, f, indent=4)
    
    # Initialize config file
    if not os.path.exists(app.config['CONFIG_FILE']):
        with open(app.config['CONFIG_FILE'], 'w') as f:
            json.dump({
                'print_settings': {
                    'default_mode': 'noir',
                    'default_duplex': 'non'
                },
                'security': {
                    'login_attempts': {}
                }
            }, f, indent=4)

def allowed_file(filename):
    """Check if file has allowed extension"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def is_locked_out(ip):
    with open(app.config['CONFIG_FILE'], 'r') as f:
        config = json.load(f)
    
    if ip in config['security']['login_attempts']:
        attempts = config['security']['login_attempts'][ip]
        if attempts['count'] >= app.config['MAX_LOGIN_ATTEMPTS']:
            time_elapsed = (datetime.now() - datetime.fromisoformat(attempts['last_attempt'])).seconds
            return time_elapsed < app.config['LOCKOUT_TIME']  # Fixed line
    return False

def record_login_attempt(ip, success):
    """Record login attempt in config"""
    with open(app.config['CONFIG_FILE'], 'r+') as f:
        config = json.load(f)
        
        if ip not in config['security']['login_attempts']:
            config['security']['login_attempts'][ip] = {'count': 0, 'last_attempt': ''}
        
        if success:
            config['security']['login_attempts'][ip]['count'] = 0
        else:
            config['security']['login_attempts'][ip]['count'] += 1
            config['security']['login_attempts'][ip]['last_attempt'] = datetime.now().isoformat()
        
        f.seek(0)
        json.dump(config, f, indent=4)
        f.truncate()

# =============================================================================
# SECURITY DECORATORS
# =============================================================================

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'logged_in' not in session:
            flash('Please log in to access this page', 'danger')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'logged_in' not in session or session.get('role') != 'admin':
            flash('Admin privileges required', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def csrf_protect(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.method == "POST":
            token = session.pop('_csrf_token', None)
            if not token or token != request.form.get('_csrf_token'):
                abort(403)
        return f(*args, **kwargs)
    return decorated

# =============================================================================
# ROUTES
# =============================================================================

@app.route('/')
def index():
    """Main public page"""
    with open(app.config['CONFIG_FILE']) as f:
        config = json.load(f)
    return render_template('index.html', 
                         default_mode=config['print_settings']['default_mode'],
                         default_duplex=config['print_settings']['default_duplex'])

@app.route('/upload', methods=['POST'])
@csrf_protect
def upload():
    """Handle file uploads from users"""
    if 'document' not in request.files:
        flash('No file selected', 'danger')
        return redirect(request.url)
    
    file = request.files['document']
    if file.filename == '':
        flash('No file selected', 'danger')
        return redirect(request.url)
    
    if not allowed_file(file.filename):
        flash('Only PDF files are allowed', 'danger')
        return redirect(request.url)
    
    try:
        # Secure filename and save
        filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{secure_filename(file.filename)}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Add to print queue
        with open(app.config['QUEUE_FILE'], 'r+') as f:
            queue = json.load(f)
            queue.append({
                'filename': filename,
                'original_name': file.filename,
                'copies': request.form.get('copies', '1'),
                'pages': request.form.get('pages', 'all'),
                'mode': request.form.get('mode', 'noir'),
                'duplex': request.form.get('duplex', 'non'),
                'timestamp': datetime.now().isoformat(),
                'status': 'pending',
                'user': session.get('username', 'anonymous'),
                'ip': request.remote_addr
            })
            f.seek(0)
            json.dump(queue, f, indent=4)
        
        flash('File uploaded successfully and added to print queue!', 'success')
        return redirect(url_for('index'))
    
    except Exception as e:
        app.logger.error(f"Upload error: {str(e)}")
        flash('An error occurred during file upload', 'danger')
        return redirect(request.url)

# =============================================================================
# AUTHENTICATION ROUTES
# =============================================================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login page"""
    if request.method == 'POST':
        if is_locked_out(request.remote_addr):
            flash('Too many failed attempts. Please try again later.', 'danger')
            return redirect(url_for('login'))
        
        username = request.form.get('username')
        password = request.form.get('password')
        
        with open(app.config['USERS_FILE']) as f:
            users = json.load(f)
        
        if username in users and check_password_hash(users[username]['password'], password):
            session.permanent = True
            session['logged_in'] = True
            session['username'] = username
            session['role'] = users[username].get('role', 'user')
            session['_csrf_token'] = secrets.token_hex(16)
            
            record_login_attempt(request.remote_addr, True)
            flash('Logged in successfully', 'success')
            
            next_page = request.args.get('next')
            return redirect(next_page or url_for('admin_dashboard'))
        else:
            record_login_attempt(request.remote_addr, False)
            flash('Invalid username or password', 'danger')
    
    return render_template('auth/login.html')

@app.route('/logout')
def logout():
    """Logout user"""
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

# =============================================================================
# ADMIN ROUTES
# =============================================================================

@app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    """Admin dashboard with print queue"""
    with open(app.config['QUEUE_FILE']) as f:
        queue = json.load(f)
    
    # Calculate statistics
    stats = {
        'pending': len([j for j in queue if j['status'] == 'pending']),
        'printing': len([j for j in queue if j['status'] == 'printing']),
        'completed': len([j for j in queue if j['status'] == 'completed']),
        'failed': len([j for j in queue if j['status'] == 'failed']),
        'total': len(queue)
    }
    
    return render_template('admin/dashboard.html', 
                         queue=queue, 
                         stats=stats,
                         csrf_token=session.get('_csrf_token'))

@app.route('/admin/queue/update', methods=['POST'])
@login_required
@admin_required
@csrf_protect
def update_queue():
    """Update print job status (AJAX endpoint)"""
    data = request.get_json()
    
    try:
        with open(app.config['QUEUE_FILE'], 'r+') as f:
            queue = json.load(f)
            
            for item in queue:
                if item['filename'] == data['filename']:
                    item['status'] = data['status']
                    if 'notes' in data:
                        item['notes'] = data['notes']
                    item['processed_by'] = session['username']
                    item['processed_at'] = datetime.now().isoformat()
                    break
            
            f.seek(0)
            json.dump(queue, f, indent=4)
        
        return jsonify({'success': True})
    
    except Exception as e:
        app.logger.error(f"Queue update error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/users')
@login_required
@admin_required
def manage_users():
    """User management page"""
    with open(app.config['USERS_FILE']) as f:
        users = json.load(f)
    
    return render_template('admin/users.html', users=users)

@app.route('/admin/settings', methods=['GET', 'POST'])
@login_required
@admin_required
def system_settings():
    """System configuration page"""
    if request.method == 'POST':
        try:
            with open(app.config['CONFIG_FILE'], 'r+') as f:
                config = json.load(f)
                config['print_settings']['default_mode'] = request.form.get('default_mode')
                config['print_settings']['default_duplex'] = request.form.get('default_duplex')
                
                f.seek(0)
                json.dump(config, f, indent=4)
                f.truncate()
            
            flash('Settings updated successfully', 'success')
        
        except Exception as e:
            app.logger.error(f"Settings update error: {str(e)}")
            flash('Failed to update settings', 'danger')
    
    with open(app.config['CONFIG_FILE']) as f:
        config = json.load(f)
    
    return render_template('admin/settings.html', settings=config['print_settings'])

# =============================================================================
# ERROR HANDLERS
# =============================================================================

@app.errorhandler(403)
def forbidden(e):
    return render_template('errors/403.html'), 403

@app.errorhandler(404)
def page_not_found(e):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('errors/500.html'), 500

# =============================================================================
# INITIALIZATION
# =============================================================================

if __name__ == '__main__':
    initialize_files()
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)