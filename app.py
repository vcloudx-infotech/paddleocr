import os
import re
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
from paddleocr import PaddleOCR
import cv2
import numpy as np

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create uploads folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize PaddleOCR
ocr = PaddleOCR(use_angle_cls=True, lang='en')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def is_valid_date(text):
    # Check for YYYY-MM-DD format
    date_pattern = r'\d{4}-\d{2}-\d{2}'
    if re.search(date_pattern, text):
        return True
    return False

def extract_oman_id_info(result):
    """
    Extract information from Oman ID card OCR results
    """
    id_info = {
        'civil_number': None,
        'expiry_date': None,
        'date_of_birth': None,
        'image': {
            'exists': True,  # Assume true for ID cards
            'confidence': 0.95
        },
        'signature': {
            'exists': False,
            'confidence': 0.0
        },
        'type': None
    }
    
    # Flatten OCR results for easier processing
    all_text = [(line[1][0].upper().replace(" ", ""), line[1][1]) for line in result[0]]
    all_text_with_space = [(line[1][0].upper(), line[1][1]) for line in result[0]]

    # --- Card Type Detection ---
    found_identity = any("IDENTITY" in t for t, _ in all_text_with_space)
    found_resident = any("RESIDENT" in t for t, _ in all_text_with_space)
    found_card = any("CARD" in t for t, _ in all_text_with_space)
    if found_identity and found_card:
        id_info['type'] = "identity"
    elif found_resident and found_card:
        id_info['type'] = "residential"

    # --- Civil Number Extraction ---
    for idx, (text, confidence) in enumerate(all_text):
        if "CIVILNUMBER" in text or "CIVIL NUMBER" in text:
            # Look for the next line with a number
            if idx + 1 < len(all_text):
                next_text, next_conf = all_text[idx + 1]
                # Accept only if it's all digits (or mostly digits)
                if re.match(r"^\d{5,}$", next_text):
                    id_info['civil_number'] = {
                        'value': next_text,
                        'confidence': next_conf
                    }
                    break

    # --- Expiry Date Extraction ---
    for idx, (text, confidence) in enumerate(all_text_with_space):
        if "EXPIRY DATE" in text or "VALID UNTIL" in text:
            if idx + 1 < len(all_text_with_space):
                next_text, next_conf = all_text_with_space[idx + 1]
                if re.match(r"\d{2}/\d{2}/\d{4}", next_text):
                    id_info['expiry_date'] = {
                        'value': next_text,
                        'confidence': next_conf
                    }
                    break

    # --- Date of Birth Extraction ---
    for idx, (text, confidence) in enumerate(all_text_with_space):
        if "DATE OF BIRTH" in text or "BIRTH DATE" in text:
            if idx + 1 < len(all_text_with_space):
                next_text, next_conf = all_text_with_space[idx + 1]
                if re.match(r"\d{2}/\d{2}/\d{4}", next_text):
                    id_info['date_of_birth'] = {
                        'value': next_text,
                        'confidence': next_conf
                    }
                    break

    # --- Signature Detection ---
    for text, confidence in all_text_with_space:
        if "SIGNATURE" in text:
            id_info['signature']['exists'] = True
            id_info['signature']['confidence'] = confidence
            break

    return id_info

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            # Read image
            img = cv2.imread(filepath)
            if img is None:
                return jsonify({'error': 'Could not read image'}), 400
            
            # Perform OCR
            result = ocr.ocr(img, cls=True)
            
            # Extract Oman ID card information
            id_info = extract_oman_id_info(result)
            
            # Clean up
            os.remove(filepath)
            
            return jsonify({
                'success': True,
                'data': id_info,
                'raw_results': result
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    return jsonify({'error': 'Invalid file type'}), 400

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "error": "Not found",
        "message": "The requested URL was not found on the server. Only /upload is available."
    }), 404

if __name__ == '__main__':
    app.run(debug=True) 