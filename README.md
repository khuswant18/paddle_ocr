# Invoice OCR Extractor

A full-stack application for extracting structured invoice data from PDF and image files using PaddleOCR. Features a Flask backend with intelligent invoice parsing and a React frontend for easy file uploads.

## Features

- 📄 **PDF & Image Support**: Upload PDF, PNG, JPG, or JPEG files
- 🔍 **Intelligent OCR**: Powered by PaddleOCR v3.0.0 with PP-OCRv5 models
- 📊 **Smart Extraction**: Automatically extracts invoice fields:
  - Invoice number, date, PO number
  - Seller & buyer information (name, address, phone, tax IDs)
  - Line items with quantities, prices, and amounts
  - Totals, subtotals, tax, and discounts
- 🎯 **Fuzzy Matching**: Handles OCR errors with intelligent field matching
- 💻 **Modern UI**: Clean React interface with real-time preview
- ✨ **Terminal-Style Output**: View extraction results in formatted summary

## Tech Stack

**Backend:**
- Python 3.8-3.12
- Flask 3.1.2 + Flask-CORS 6.0.1
- PaddleOCR 3.0.0 + PaddlePaddle 3.0.0
- pdf2image, Pillow, rapidfuzz

**Frontend:**
- React 18.2.0
- Axios 1.6.2
- CSS3 with dark theme

## Prerequisites

- **Python 3.8-3.12** (Python 3.12 recommended)
- **Node.js 14+** and npm
- **pip** (Python package manager)
- **poppler-utils** (for PDF processing)
  - macOS: `brew install poppler`
  - Ubuntu/Debian: `sudo apt-get install poppler-utils`
  - Windows: Download from [poppler releases](https://github.com/oschwartz10612/poppler-windows/releases)

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd ocr_screen
```

### 2. Backend Setup

#### Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
# macOS/Linux:
source .venv/bin/activate

# Windows (cmd):
.venv\Scripts\activate.bat

# Windows (PowerShell):
.venv\Scripts\Activate.ps1
```

#### Install Python Dependencies

```bash
pip install -r requirements.txt
```

**requirements.txt includes:**
- PySide6
- paddleocr==3.0.0
- paddlepaddle==3.0.0
- setuptools
- Pillow
- pdf2image
- rapidfuzz
- flask
- flask-cors

> **Note**: First run will download PaddleOCR models (~100MB) automatically to `~/.paddlex/official_models/`

### 3. Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install Node dependencies
npm install

# Return to root directory
cd ..
```

## Running the Application

### Option 1: Run Both Services Separately

#### Terminal 1: Start Backend

```bash
# Activate virtual environment
source .venv/bin/activate  # macOS/Linux
# or
.venv\Scripts\activate.bat  # Windows

# Start Flask backend
python3 backend/app.py
```

Backend will start at: **http://localhost:5000**

#### Terminal 2: Start Frontend

```bash
# Navigate to frontend directory
cd frontend

# Start React development server
npm start
```

Frontend will open automatically at: **http://localhost:3000**

### Option 2: Using the Start Script (macOS/Linux)

```bash
# Make script executable (first time only)
chmod +x start_backend.sh

# Start backend in background
./start_backend.sh

# In another terminal, start frontend
cd frontend && npm start
```

## Usage

1. **Open the Application**: Navigate to http://localhost:3000
2. **Upload File**: Click "Choose File" and select a PDF or image
3. **Extract Data**: Click "Upload & Extract" button
4. **View Results**: 
   - Left panel: Document preview
   - Right panel: Extracted invoice data in terminal-style format

### Supported File Types

- PDF (.pdf)
- JPEG (.jpg, .jpeg)
- PNG (.png)

### API Endpoints

**Health Check:**
```bash
GET http://localhost:5000/api/health
```

**Upload & Extract:**
```bash
POST http://localhost:5000/api/upload
Content-Type: multipart/form-data
Body: file=<your-file>
```

**Response Format:**
```json
{
  "success": true,
  "preview_images": ["data:image/jpeg;base64,..."],
  "extracted_text": "Full OCR text...",
  "invoice_data": {
    "invoice_number": "84346",
    "invoice_date": "10/02/2025",
    "po_number": "3965647",
    "seller_name": "CENTURIAN INTERNATIONAL CORPORATION",
    "buyer_name": "PRINCEPAN CORPORATION",
    "items": [...],
    "subtotal": 2964.29,
    "grand_total": 3320.00
  },
  "summary": "Formatted terminal output..."
}
```

## Testing

### Test Backend with Sample Files

```bash
# Activate virtual environment
source .venv/bin/activate

# Test with command-line tool
python3 app/invoice_extractor.py sample1.jpg

# Or use the test script
python3 test_backend.py
```

### Test API with curl

```bash
# Health check
curl http://localhost:5000/api/health

# Upload test file
curl -X POST http://localhost:5000/api/upload \
  -F "file=@sample1.jpg"
```

## Project Structure

```
ocr_screen/
├── app/
│   ├── invoice_extractor.py    # Invoice data extraction logic
│   ├── ocr_utils.py             # PaddleOCR wrapper
│   └── __pycache__/
├── backend/
│   ├── app.py                   # Flask API server
│   └── __pycache__/
├── frontend/
│   ├── public/
│   │   └── index.html
│   ├── src/
│   │   ├── App.js              # Main React component
│   │   ├── App.css             # Styling
│   │   ├── index.js            # React entry point
│   │   └── index.css
│   ├── package.json
│   └── node_modules/
├── .venv/                       # Python virtual environment
├── requirements.txt             # Python dependencies
├── sample1.jpg                  # Sample invoice image
├── sample1.pdf                  # Sample invoice PDF
├── README.md                    # This file
├── start_backend.sh             # Backend startup script
└── test_backend.py              # Backend test script
```

## Troubleshooting

### Port 5000 Already in Use (macOS)

If you see "Address already in use" error:

```bash
# Option 1: Kill process using port 5000
lsof -ti:5000 | xargs kill -9

# Option 2: Disable AirPlay Receiver
# System Preferences → General → AirDrop & Handoff → 
# Uncheck "AirPlay Receiver"
```

### PaddleOCR Models Not Downloading

Models download automatically on first run. If they fail:

```bash
# Clear cache and retry
rm -rf ~/.paddlex/official_models/
python3 backend/app.py
```

### PDF Processing Errors

Ensure poppler is installed:

```bash
# macOS
brew install poppler

# Ubuntu/Debian
sudo apt-get install poppler-utils

# Verify installation
which pdftoppm
```

### React Build Warnings

Safe to ignore these warnings during development:
```
Warning: ReactDOM.render is no longer supported in React 18
```

### Backend Crashes on Certain Invoices

Check logs:
```bash
tail -f backend.log
```

Common issues:
- Amount parsing errors (fixed with newline validation)
- Missing fields (handled gracefully with default values)
- Large PDF files (may need timeout adjustments)

## Development

### Backend Development

```bash
# Run with auto-reload
FLASK_ENV=development python3 backend/app.py

# Run tests
python3 test_backend.py
```

### Frontend Development

```bash
cd frontend

# Run dev server
npm start

# Build for production
npm run build
```

## Performance Notes

- **First Request**: 10-15 seconds (model loading)
- **Subsequent Requests**: 2-5 seconds per page
- **PDF Pages**: ~3-4 seconds per page
- **Model Size**: ~100MB (downloaded once)

## Known Limitations

- OCR accuracy depends on image quality
- Handwritten text not supported
- Complex multi-column layouts may need adjustment
- Best results with clear, high-resolution scans

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/improvement`)
3. Commit changes (`git commit -am 'Add new feature'`)
4. Push to branch (`git push origin feature/improvement`)
5. Create Pull Request

## License

This project is licensed under the MIT License.

## Acknowledgments

- **PaddleOCR**: Awesome OCR library by PaddlePaddle
- **FastInvoiceExtractor**: Custom fuzzy matching engine
- **React**: Frontend framework

## Support

For issues and questions:
1. Check [Troubleshooting](#troubleshooting) section
2. Review backend logs: `tail -f backend.log`
3. Open an issue with:
   - Error message
   - Sample file (if possible)
   - Steps to reproduce

---

**Made with ❤️ using PaddleOCR and React**
