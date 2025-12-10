from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
from pdf2image import convert_from_path
import tempfile
import os
import base64
from io import BytesIO
import sys
import os

# Add parent directory to path to import app modules
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

# Import from app directory (not app package)
import importlib.util

# Load ocr_utils
ocr_utils_path = os.path.join(parent_dir, 'app', 'ocr_utils.py')
spec = importlib.util.spec_from_file_location("ocr_utils", ocr_utils_path)
ocr_utils = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ocr_utils)

# Load invoice_extractor
invoice_extractor_path = os.path.join(parent_dir, 'app', 'invoice_extractor.py')
spec = importlib.util.spec_from_file_location("invoice_extractor", invoice_extractor_path)
invoice_extractor_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(invoice_extractor_module)

OCRProcessor = ocr_utils.OCRProcessor
FastInvoiceExtractor = invoice_extractor_module.FastInvoiceExtractor
from dataclasses import asdict

app = Flask(__name__)
CORS(app)  # Enable CORS for React frontend

# Initialize OCR processor and extractor
ocr_processor = OCRProcessor(lang='en')
invoice_extractor = FastInvoiceExtractor(fuzzy_threshold=65)

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type. Please upload PDF, PNG, JPG, or JPEG'}), 400
    
    try:
        # Save uploaded file temporarily
        temp_dir = tempfile.mkdtemp() 
        filename = secure_filename(file.filename)
        file_path = os.path.join(temp_dir, filename)
        file.save(file_path) 
        
        # Convert PDF to images or process single image
        if filename.lower().endswith('.pdf'):
            images = convert_from_path(file_path)
            image_paths = []
            preview_images = []
            
            for i, img in enumerate(images):
                img_path = os.path.join(temp_dir, f'page_{i+1}.jpg')
                img.save(img_path, 'JPEG')
                image_paths.append(img_path)
                
                # Convert to base64 for preview
                buffered = BytesIO()
                img.save(buffered, format="JPEG")
                img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
                preview_images.append(f"data:image/jpeg;base64,{img_base64}")
        else:
            image_paths = [file_path]
            # Load image for preview
            from PIL import Image
            img = Image.open(file_path)
            buffered = BytesIO()
            img.save(buffered, format="JPEG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
            preview_images = [f"data:image/jpeg;base64,{img_base64}"]
        
        # Perform OCR on all pages
        full_text = ""
        for img_path in image_paths:
            text = ocr_processor.process_image(img_path) or ""
            full_text += text + "\n"
        
        # Extract invoice data using FastInvoiceExtractor
        invoice_data = invoice_extractor.extract(full_text)
        
        # Generate summary text like the terminal output
        summary_text = invoice_extractor.get_summary(invoice_data) if invoice_data else "No data extracted"
        
        # Convert to dict for JSON response
        invoice_dict = {}
        if invoice_data:
            try:
                invoice_dict = asdict(invoice_data)
            except:
                # Fallback if dataclass conversion fails
                invoice_dict = {
                    'invoice_number': getattr(invoice_data, 'invoice_number', ''),
                    'invoice_date': getattr(invoice_data, 'invoice_date', ''),
                    'due_date': getattr(invoice_data, 'due_date', ''),
                    'seller_name': getattr(invoice_data, 'seller_name', ''),
                    'seller_address': getattr(invoice_data, 'seller_address', ''),
                    'seller_gstin': getattr(invoice_data, 'seller_gstin', ''),
                    'buyer_name': getattr(invoice_data, 'buyer_name', ''),
                    'buyer_address': getattr(invoice_data, 'buyer_address', ''),
                    'buyer_gstin': getattr(invoice_data, 'buyer_gstin', ''),
                    'subtotal': getattr(invoice_data, 'subtotal', '0.00'),
                    'cgst': getattr(invoice_data, 'cgst', '0.00'),
                    'sgst': getattr(invoice_data, 'sgst', '0.00'),
                    'igst': getattr(invoice_data, 'igst', '0.00'),
                    'grand_total': getattr(invoice_data, 'grand_total', '0.00'),
                    'items': getattr(invoice_data, 'items', [])
                }
        
        result = {
            'success': True,
            'preview_images': preview_images,
            'extracted_text': full_text,
            'invoice_data': invoice_dict,
            'summary': summary_text
        }
        
        # Cleanup
        for img_path in image_paths:
            if os.path.exists(img_path):
                os.unlink(img_path)
        if os.path.exists(file_path):
            os.unlink(file_path)
        os.rmdir(temp_dir)
        
        return jsonify(result)
    
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error processing file: {str(e)}")
        print(f"Full traceback:\n{error_details}")
        return jsonify({'error': f'Error processing file: {str(e)}'}), 500

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'message': 'OCR API is running'})

if __name__ == '__main__':
    print("Starting OCR Invoice Extractor API...")
    print("API will be available at http://localhost:5000")
    app.run(debug=True, port=5000)
