import os
import time
from flask import Flask, request, jsonify, send_from_directory, abort
import rembg
from werkzeug.utils import secure_filename
from PIL import Image
import io
import uuid
import logging
from logging.handlers import RotatingFileHandler

# Initialize Flask app
app = Flask(__name__, static_folder='static')

# Configuration
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY", os.urandom(24).hex()),
    PORT=int(os.environ.get("PORT", 10000)),
    UPLOAD_FOLDER='static/uploads',
    RESULT_FOLDER='static/results',
    MAX_CONTENT_LENGTH=16 * 1024 * 1024,  # 16MB
    ALLOWED_EXTENSIONS={'png', 'jpg', 'jpeg', 'webp'},
    MODEL_NAME=os.environ.get("MODEL_NAME", "u2net"),
    AUTO_CLEANUP=True,
    CLEANUP_OLDER_THAN=3600  # 1 hour
)

# Logging
handler = RotatingFileHandler('app.log', maxBytes=10000, backupCount=3)
handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
app.logger.addHandler(handler)
app.logger.setLevel(logging.INFO)

# Create directories
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['RESULT_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def clean_old_files():
    if not app.config['AUTO_CLEANUP']:
        return
    current_time = time.time()
    for folder in [app.config['UPLOAD_FOLDER'], app.config['RESULT_FOLDER']]:
        for filename in os.listdir(folder):
            file_path = os.path.join(folder, filename)
            if os.path.isfile(file_path):
                file_age = current_time - os.path.getmtime(file_path)
                if file_age > app.config['CLEANUP_OLDER_THAN']:
                    os.remove(file_path)

@app.route('/')
def home():
    return send_from_directory('static', 'index.html')

@app.route('/remove-bg', methods=['POST'])
def remove_bg():
    clean_old_files()
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
        
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type'}), 400

    try:
        # Save original
        file_ext = secure_filename(file.filename).split('.')[-1].lower()
        unique_id = uuid.uuid4().hex
        filename = f"{unique_id}.{file_ext}"
        original_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(original_path)

        # Process image
        with open(original_path, 'rb') as f:
            output_bytes = rembg.remove(
                f.read(),
                session=rembg.new_session(model_name=app.config['MODEL_NAME'])
            )

        # Save result
        result_filename = f"{unique_id}_removed.png"
        result_path = os.path.join(app.config['RESULT_FOLDER'], result_filename)
        with open(result_path, 'wb') as f:
            f.write(output_bytes)

        return jsonify({
            'success': True,
            'original': f'/static/uploads/{filename}',
            'result': f'/static/results/{result_filename}',
            'download': f'/download/{result_filename}'
        })

    except Exception as e:
        app.logger.error(f"Error processing image: {str(e)}")
        return jsonify({'error': 'Processing failed'}), 500

@app.route('/download/<filename>')
def download(filename):
    try:
        return send_from_directory(
            app.config['RESULT_FOLDER'],
            filename,
            as_attachment=True,
            download_name=f"no_bg_{filename}"
        )
    except FileNotFoundError:
        abort(404)

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'}), 200

# Change this line at the bottom:
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))  # Keep 10000 as fallback
    app.run(host='0.0.0.0', port=port)
