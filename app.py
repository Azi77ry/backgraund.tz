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

app = Flask(__name__, static_folder='static')

# ========== Configuration ==========
app.config.from_mapping(
    SECRET_KEY=os.environ.get("SECRET_KEY", os.urandom(24).hex()),
    PORT=int(os.environ.get("PORT", 10000)),
    UPLOAD_FOLDER='static/uploads',
    RESULT_FOLDER='static/results',
    MAX_CONTENT_LENGTH=16 * 1024 * 1024,  # 16MB
    ALLOWED_EXTENSIONS={'png', 'jpg', 'jpeg', 'webp'},
    MODEL_NAME='u2net',  # Options: 'u2netp', 'u2net_human_seg'
    AUTO_CLEANUP=True,
    CLEANUP_OLDER_THAN=3600,  # 1 hour in seconds
    LOG_FILE='app.log',
    LOG_LEVEL=logging.INFO
)

# ========== Setup Logging ==========
handler = RotatingFileHandler(
    app.config['LOG_FILE'],
    maxBytes=10000,
    backupCount=3
)
handler.setLevel(app.config['LOG_LEVEL'])
handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
app.logger.addHandler(handler)
app.logger.setLevel(app.config['LOG_LEVEL'])

# ========== Directory Setup ==========
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['RESULT_FOLDER'], exist_ok=True)

# ========== Helper Functions ==========
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def clean_old_files():
    """Remove files older than CLEANUP_OLDER_THAN seconds"""
    if not app.config['AUTO_CLEANUP']:
        return
    
    current_time = time.time()
    for folder in [app.config['UPLOAD_FOLDER'], app.config['RESULT_FOLDER']]:
        try:
            for filename in os.listdir(folder):
                file_path = os.path.join(folder, filename)
                if os.path.isfile(file_path):
                    file_age = current_time - os.path.getmtime(file_path)
                    if file_age > app.config['CLEANUP_OLDER_THAN']:
                        try:
                            os.remove(file_path)
                            app.logger.info(f"Cleaned up old file: {file_path}")
                        except Exception as e:
                            app.logger.error(f"Error removing {file_path}: {str(e)}")
        except Exception as e:
            app.logger.error(f"Error cleaning {folder}: {str(e)}")

# ========== Routes ==========
@app.route('/')
def serve_frontend():
    return send_from_directory('static', 'index.html')

@app.route('/remove-bg', methods=['POST'])
def remove_background():
    clean_old_files()
    
    # Validate input
    if 'file' not in request.files:
        app.logger.warning("No file part in request")
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        app.logger.warning("Empty filename in request")
        return jsonify({'error': 'No selected file'}), 400
    
    if not allowed_file(file.filename):
        app.logger.warning(f"Invalid file type attempted: {file.filename}")
        return jsonify({'error': 'Invalid file type. Allowed: PNG, JPG, JPEG, WEBP'}), 400
    
    try:
        # Generate unique filenames
        file_ext = secure_filename(file.filename).rsplit('.', 1)[1].lower()
        unique_id = uuid.uuid4().hex
        filename = f"{unique_id}.{file_ext}"
        original_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # Save original with error handling
        try:
            file.save(original_path)
        except IOError as e:
            app.logger.error(f"Failed to save file {filename}: {str(e)}")
            return jsonify({'error': 'Failed to save file'}), 500
        
        # Process image
        try:
            with open(original_path, 'rb') as f:
                img_bytes = f.read()
            
            output_bytes = rembg.remove(
                img_bytes,
                session=rembg.new_session(model_name=app.config['MODEL_NAME'])
            )
            
            # Optimize output
            try:
                output_img = Image.open(io.BytesIO(output_bytes))
                optimized_bytes = io.BytesIO()
                output_img.save(optimized_bytes, format='PNG', optimize=True)
                optimized_bytes.seek(0)
                
                # Save result
                result_filename = f"{unique_id}_removed.png"
                result_path = os.path.join(app.config['RESULT_FOLDER'], result_filename)
                with open(result_path, 'wb') as f:
                    f.write(optimized_bytes.getvalue())
                
                app.logger.info(f"Successfully processed image: {filename}")
                return jsonify({
                    'success': True,
                    'original': f'/static/uploads/{filename}',
                    'result': f'/static/results/{result_filename}',
                    'download': f'/download/{result_filename}'
                })
            except Exception as e:
                app.logger.error(f"Image optimization failed: {str(e)}")
                return jsonify({'error': 'Image processing failed'}), 500
                
        except Exception as e:
            app.logger.error(f"Background removal failed: {str(e)}")
            return jsonify({'error': 'Background removal failed'}), 500
            
    except Exception as e:
        app.logger.error(f"Unexpected error: {str(e)}")
        return jsonify({'error': 'Server error'}), 500

@app.route('/download/<filename>')
def download_result(filename):
    try:
        if not os.path.exists(os.path.join(app.config['RESULT_FOLDER'], filename)):
            app.logger.warning(f"Download requested for non-existent file: {filename}")
            abort(404)
            
        return send_from_directory(
            app.config['RESULT_FOLDER'],
            filename,
            as_attachment=True,
            download_name=f"no_bg_{filename}"
        )
    except Exception as e:
        app.logger.error(f"Download failed: {str(e)}")
        abort(500)

@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

# ========== Error Handlers ==========
@app.errorhandler(404)
def not_found_error(error):
    return jsonify({'error': 'Resource not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

# ========== Main Execution ==========
import os
from flask import Flask

app = Flask(__name__)

# Add this at the bottom of your file:
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))  # Use Render's PORT or default to 10000
    app.run(host='0.0.0.0', port=port)  # Must bind to 0.0.0.0