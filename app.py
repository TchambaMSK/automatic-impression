from flask import Flask, render_template, request, redirect
import os
import json
from datetime import datetime

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
QUEUE_FILE = 'file_queue.json'

# Assure que le dossier uploads existe
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Page principale avec formulaire
@app.route('/')
def index():
    return render_template('index.html')

# Route de traitement du formulaire
@app.route('/upload', methods=['POST'])
def upload():
    file = request.files['document']
    copies = request.form.get('copies')
    pages = request.form.get('pages')
    mode = request.form.get('mode')

    if file:
        filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        # Charger ou créer la file
        if os.path.exists(QUEUE_FILE):
            with open(QUEUE_FILE, 'r') as f:
                queue = json.load(f)
        else:
            queue = []

        # Ajouter à la file
        queue.append({
            'filename': filename,
            'copies': copies,
            'pages': pages,
            'mode': mode
        })

        # Enregistrer la file
        with open(QUEUE_FILE, 'w') as f:
            json.dump(queue, f, indent=4)

    return redirect('/')

# Lancement local (facultatif, pour Codespaces uniquement)
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
