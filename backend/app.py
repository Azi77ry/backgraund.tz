import os
import time
from flask import Flask, request, jsonify, send_from_directory, abort
import rembg
from werkzeug.utils import secure_filename
from PIL import Image
import io
import uuid

app = Flask(__name__, static_folder='static')

# Configuration
app.config.update({
    'UPLOAD_FOLDER': 'static/uploads',
    'RESULT_FOLDER': 'static/results',
    'MAX_CONTENT_LENGTH': 16 * 1024 * 1024,  # 16MB
    'ALLOWED_EXTENSIONS': {'png', 'jpg', 'jpeg', 'webp'},
    'MODEL_NAME': 'u2net',  # Can be changed to 'u2netp', 'u2net_human_seg', etc.
    'AUTO_CLEANUP': True,  # Clean up old files automatically
    'CLEANUP_OLDER_THAN': 3600  # 1 hour in seconds
})

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['RESULT_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def clean_old_files():
    """Remove files older than CLEANUP_OLDER_THAN seconds"""
    if not app.config['AUTO_CLEANUP']:
        return
    
    current_time = time.time()
    for folder in [app.config['UPLOAD_FOLDER'], app.config['RESULT_FOLDER']]:
        for filename in os.listdir(folder):
            file_path = os.path.join(folder, filename)
            try:
                if os.path.isfile(file_path) and (current_time - os.path.getmtime(file_path)) > app.config['CLEANUP_OLDER_THAN']:
                    os.remove(file_path)
            except Exception as e:
                app.logger.error(f"Error cleaning up file {file_path}: {e}")
                
@app.route('/frontend/<path:filename>')
def frontend_files(filename):
    return send_from_directory('../frontend', filename)               

@app.route('/')
def serve_frontend():
    return send_from_directory('../frontend', 'index.html')

@app.route('/remove-bg', methods=['POST'])
def remove_background():
    clean_old_files()  # Clean up old files before processing
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type. Allowed: PNG, JPG, JPEG, WEBP'}), 400
    
    try:
        # Generate unique filename
        file_ext = secure_filename(file.filename).rsplit('.', 1)[1].lower()
        unique_id = uuid.uuid4().hex
        filename = f"{unique_id}.{file_ext}"
        original_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # Save original
        file.save(original_path)
        
        # Process image
        with open(original_path, 'rb') as f:
            img_bytes = f.read()
        
        output_bytes = rembg.remove(
            img_bytes,
            session=rembg.new_session(model_name=app.config['MODEL_NAME'])
        )
        
        # Optimize output
        output_img = Image.open(io.BytesIO(output_bytes))
        optimized_bytes = io.BytesIO()
        output_img.save(optimized_bytes, format='PNG', optimize=True)
        optimized_bytes.seek(0)
        
        # Save result
        result_filename = f"{unique_id}_removed.png"
        result_path = os.path.join(app.config['RESULT_FOLDER'], result_filename)
        with open(result_path, 'wb') as f:
            f.write(optimized_bytes.getvalue())
        
        return jsonify({
            'success': True,
            'original': f'/static/uploads/{filename}',
            'result': f'/static/results/{result_filename}',
            'download': f'/download/{result_filename}'
        })
    except Exception as e:
        app.logger.error(f"Error processing image: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to process image. Please try again.'
        }), 500

@app.route('/download/<filename>')
def download_result(filename):
    try:
        return send_from_directory(
            app.config['RESULT_FOLDER'],
            filename,
            as_attachment=True,
            download_name=f"background_removed_{filename}"
        )
    except FileNotFoundError:
        abort(404)

@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)