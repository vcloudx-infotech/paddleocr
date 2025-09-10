import os
import re
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
from paddleocr import PaddleOCR
import cv2
import numpy as np
from difflib import SequenceMatcher
import logging

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create uploads folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize PaddleOCR
ocr = PaddleOCR(use_angle_cls=True, lang='en')

# Configure minimal logging
logging.basicConfig(level=logging.ERROR)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def preprocess_image_for_ocr(img):
    """
    Apply single preprocessing for maximum speed
    """
    # Convert to grayscale and apply CLAHE in one step
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    processed_img = clahe.apply(gray)
    
    return processed_img

def similarity(a, b):
    """Calculate similarity between two strings"""
    return SequenceMatcher(None, a, b).ratio()

def fuzzy_match(text, patterns, threshold=0.6):
    """Find the best matching pattern for the given text"""
    best_match = None
    best_score = 0
    
    for pattern in patterns:
        score = similarity(text, pattern)
        if score > best_score and score >= threshold:
            best_score = score
            best_match = pattern
    
    return best_match, best_score

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
        'signature': {
            'exists': False,
            'confidence': 0.0
        },
        'type': None
    }
    
    if not result or len(result) == 0 or not result[0]:
        return id_info
    
    # Extract text from OCR result
    all_results = [(line[1][0], line[1][1]) for line in result[0]]
    
    # Flatten for processing
    all_text = [(line[0].upper().replace(" ", ""), line[1]) for line in all_results]
    all_text_with_space = [(line[0].upper(), line[1]) for line in all_results]

    # --- Card Type Detection ---
    found_identity = False
    found_resident = False
    found_card = False
    
    for text, conf in all_text_with_space:
        if "IDENTITY" in text or "IDENTIFICATION" in text:
            found_identity = True
        if "RESIDENT" in text or "RESIDENTIAL" in text:
            found_resident = True
        if "CARD" in text:
            found_card = True
    
    if found_identity and found_card:
        id_info['type'] = "identity"
    elif found_resident and found_card:
        id_info['type'] = "residential"
    elif found_identity:
        id_info['type'] = "identity"
    elif found_resident:
        id_info['type'] = "residential"

    # --- Civil Number Extraction (Optimized) ---
    best_civil = None
    best_civil_conf = 0
    
    # Single pass through all text
    for idx, (text, confidence) in enumerate(all_text):
        # Check for civil number patterns
        if any(pattern in text for pattern in ["CIVILNUMBER", "CIVIL NUMBER", "CIVIL NO", "CIVIL ID", "ID NUMBER"]):
            # Look for numbers in current and next line
            for i in range(2):  # Check current and next line only
                if idx + i < len(all_text):
                    check_text, check_conf = all_text[idx + i]
                    numbers = re.findall(r'\d{7,}', check_text)  # Look for 7+ digit numbers
                    for num in numbers:
                        if check_conf > best_civil_conf:
                            best_civil = num
                            best_civil_conf = check_conf
        else:
            # Also check for standalone 7+ digit numbers
            numbers = re.findall(r'\d{7,}', text)
            for num in numbers:
                if confidence > best_civil_conf:
                    best_civil = num
                    best_civil_conf = confidence
    
    if best_civil:
        id_info['civil_number'] = {
            'value': best_civil,
            'confidence': best_civil_conf
        }

    # --- Date Extraction (Optimized) ---
    best_expiry = None
    best_expiry_conf = 0
    best_birth = None
    best_birth_conf = 0
    
    # Single pass through all text
    for idx, (text, confidence) in enumerate(all_text_with_space):
        # Check for date patterns
        if any(pattern in text for pattern in ["EXPIRY DATE", "EXPIRY", "VALID UNTIL", "VALID", "EXPIRES"]):
            # Look for dates in current and next line
            for i in range(2):
                if idx + i < len(all_text_with_space):
                    check_text, check_conf = all_text_with_space[idx + i]
                    dates = re.findall(r'\d{2}/\d{2}/\d{4}', check_text)
                    for date in dates:
                        if check_conf > best_expiry_conf:
                            best_expiry = date
                            best_expiry_conf = check_conf
        elif any(pattern in text for pattern in ["DATE OF BIRTH", "BIRTH DATE", "BIRTH", "DOB", "BORN"]):
            # Look for dates in current and next line
            for i in range(2):
                if idx + i < len(all_text_with_space):
                    check_text, check_conf = all_text_with_space[idx + i]
                    dates = re.findall(r'\d{2}/\d{2}/\d{4}', check_text)
                    for date in dates:
                        if check_conf > best_birth_conf:
                            best_birth = date
                            best_birth_conf = check_conf
        else:
            # Check for standalone dates
            dates = re.findall(r'\d{2}/\d{2}/\d{4}', text)
            for date in dates:
                year = int(date.split('/')[-1])
                if year > 2020:  # Likely expiry date
                    if confidence > best_expiry_conf:
                        best_expiry = date
                        best_expiry_conf = confidence
                elif year < 2010:  # Likely birth date
                    if confidence > best_birth_conf:
                        best_birth = date
                        best_birth_conf = confidence
    
    if best_expiry:
        id_info['expiry_date'] = {
            'value': best_expiry,
            'confidence': best_expiry_conf
        }
    
    if best_birth:
        id_info['date_of_birth'] = {
            'value': best_birth,
            'confidence': best_birth_conf
        }

    # --- Signature Detection ---
    for text, confidence in all_text_with_space:
        if "SIGNATURE" in text:
            id_info['signature']['exists'] = True
            id_info['signature']['confidence'] = max(id_info['signature']['confidence'], confidence)
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
            # Get file size in MB
            file_size_bytes = os.path.getsize(filepath)
            file_size_mb = round(file_size_bytes / (1024 * 1024), 2)
            
            # Read image
            img = cv2.imread(filepath)
            if img is None:
                return jsonify({'error': 'Could not read image'}), 400
            
            # Preprocess image with single technique
            processed_img = preprocess_image_for_ocr(img)
            
            # Perform single OCR call
            result = ocr.ocr(processed_img, cls=True)
            
            # Extract Oman ID card information
            id_info = extract_oman_id_info(result)
            
            # Print extracted values for debugging
            print(f"Civil Number: {id_info.get('civil_number', {}).get('value', 'NOT FOUND')}")
            print(f"Expiry Date: {id_info.get('expiry_date', {}).get('value', 'NOT FOUND')}")
            print(f"Date of Birth: {id_info.get('date_of_birth', {}).get('value', 'NOT FOUND')}")
            print(f"Card Type: {id_info.get('type', 'NOT DETECTED')}")
            print(f"File Size: {file_size_mb} MB")
            
            # Clean up only on successful processing
            os.remove(filepath)
            
            return jsonify({
                'success': True,
                'data': id_info,
                'file_info': {
                    'size_mb': file_size_mb
                }
            })
            
        except Exception as e:
            logger.error(f"Error processing image: {str(e)} and Filename is :: {filename}")
            # Don't delete file on error - keep it for debugging
            return jsonify({'error': str(e)}), 500
    
    return jsonify({'error': 'Invalid file type'}), 400

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "error": "Not found",
        "message": "The requested URL was not found on the server. Only /upload is available."
    }), 404

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0') 