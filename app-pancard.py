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

def is_pan_number(text):
    # Check for PAN number format (alphanumeric 10 characters)
    pan_pattern = r'[A-Z0-9]{10}'
    return bool(re.match(pan_pattern, text))

def extract_pan_info(result):
    pan_info = {
        'pan_number': None,
        'name': None,
        'father_name': None,
        'dob': None,
        'signature': 'Not Available'
    }
    
    # Process each line of OCR result
    for i, line in enumerate(result[0]):
        text = line[1][0].strip()  # The detected text
        confidence = line[1][1]  # Confidence score
        
        # Skip low confidence results
        if confidence < 0.7:
            continue
            
        # Extract PAN number
        if is_pan_number(text):
            pan_info['pan_number'] = {
                'text': text,
                'confidence': float(confidence)
            }
            continue
            
        # Extract Date of Birth
        if is_valid_date(text):
            pan_info['dob'] = {
                'text': text,
                'confidence': float(confidence)
            }
            continue
            
        # Extract Name (look for label and next line)
        if 'Name' in text and not "Father's Name" in text:
            # Check next line for the actual name
            if i + 1 < len(result[0]):
                next_text = result[0][i + 1][1][0].strip()
                next_confidence = result[0][i + 1][1][1]
                # Check if it's a valid name (not a label and not a PAN number)
                if (next_text.isupper() and 
                    len(next_text.split()) >= 2 and 
                    not is_pan_number(next_text) and 
                    not 'Name' in next_text):
                    pan_info['name'] = {
                        'text': next_text,
                        'confidence': float(next_confidence)
                    }
            continue
            
        # Extract Father's Name (look for label and next line)
        if "Father's Name" in text or "f/Father's Name" in text:
            # Check next line for the actual father's name
            if i + 1 < len(result[0]):
                next_text = result[0][i + 1][1][0].strip()
                next_confidence = result[0][i + 1][1][1]
                # Check if it's a valid name (not a label and not a PAN number)
                if (next_text.isupper() and 
                    len(next_text.split()) >= 2 and 
                    not is_pan_number(next_text) and 
                    not "Father's Name" in next_text):
                    pan_info['father_name'] = {
                        'text': next_text,
                        'confidence': float(next_confidence)
                    }
            continue
            
        # Check for signature
        if 'Signature' in text or '/Signature' in text:
            pan_info['signature'] = 'Available'
    
    return pan_info

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
            
            # Extract PAN card information
            pan_info = extract_pan_info(result)
            
            # Clean up
            os.remove(filepath)
            
            return jsonify({
                'success': True,
                'data': pan_info
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    return jsonify({'error': 'File type not allowed'}), 400

if __name__ == '__main__':
    app.run(debug=True) 