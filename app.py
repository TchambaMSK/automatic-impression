from flask import Flask, render_template, request, redirect, jsonify
import os
import json
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB limit
app.config['ALLOWED_EXTENSIONS'] = {'pdf'}
QUEUE_FILE = 'file_queue.json'

# Create upload directory if not exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    # Validate all form fields
    if 'document' not in request.files:
        return redirect(request.url)
    
    file = request.files['document']
    copies = request.form.get('copies', '1')
    pages = request.form.get('pages', 'all')
    mode = request.form.get('mode', 'noir')
    duplex = request.form.get('duplex', 'non')

    # Validate PDF file
    if file.filename == '':
        return redirect(request.url)
    
    if not (file and allowed_file(file.filename)):
        return redirect(request.url)

    try:
        # Save file with secure filename
        filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{secure_filename(file.filename)}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Update queue
        queue = []
        if os.path.exists(QUEUE_FILE):
            with open(QUEUE_FILE, 'r') as f:
                queue = json.load(f)

        queue.append({
            'filename': filename,
            'copies': int(copies),
            'pages': pages,
            'mode': mode,
            'duplex': duplex,
            'timestamp': datetime.now().isoformat(),
            'status': 'pending'
        })

        with open(QUEUE_FILE, 'w') as f:
            json.dump(queue, f, indent=4, default=str)

        return jsonify({'success': True, 'message': 'File added to queue!'})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# API endpoint to get queue status (optional)
@app.route('/queue')
def get_queue():
    try:
        if os.path.exists(QUEUE_FILE):
            with open(QUEUE_FILE, 'r') as f:
                return jsonify(json.load(f))
        return jsonify([])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)