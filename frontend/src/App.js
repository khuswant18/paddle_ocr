import React, { useState } from 'react';
import axios from 'axios';
import './App.css';
function App() {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [previewImages, setPreviewImages] = useState([]);
  const [invoiceData, setInvoiceData] = useState(null);
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState(null);

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      setFile(selectedFile);
      setError(null);
      setPreviewImages([]);
      setInvoiceData(null);
      setSummary(null);
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setError('Please select a file first');
      return;
    }

    setLoading(true);
    setError(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post('http://localhost:5000/api/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      setPreviewImages(response.data.preview_images);
      setInvoiceData(response.data.invoice_data);
      setSummary(response.data.summary);
    } catch (err) {
      setError(err.response?.data?.error || 'Error processing file');
      console.error('Upload error:', err);
    } finally {
      setLoading(false);
    }
  };

  const renderInvoiceData = (summaryText) => {
    if (!summaryText) return null;

    return (
      <div className="invoice-data">
        <h3>📄 Invoice Summary</h3>
        <pre className="summary-text">
          {summaryText}
        </pre>
      </div>
    );
  };

  return (
    <div className="App">
      <header className="app-header">
        <h1>📄 PDF Invoice Extractor</h1>
        <p>Upload PDF or image files to extract invoice data using OCR</p>
      </header>

      <div className="upload-section">
        <input
          type="file"
          accept=".pdf,.jpg,.jpeg,.png"
          onChange={handleFileChange}
          id="file-input"
        />
        <label htmlFor="file-input" className="file-label">
          {file ? file.name : 'Choose PDF or Image'}
        </label>
        <button onClick={handleUpload} disabled={loading} className="upload-btn">
          {loading ? '⏳ Processing...' : '🚀 Upload & Extract'}
        </button>
      </div>

      {error && <div className="error-message">❌ {error}</div>}

      {(previewImages.length > 0 || summary) && (
        <div className="content-container">
          <div className="left-panel">
            <h2>📋 Document Preview</h2>
            <div className="preview-images">
              {previewImages.map((img, idx) => (
                <div key={idx} className="preview-item">
                  <img src={img} alt={`Page ${idx + 1}`} className="preview-image" />
                  <p className="page-label">Page {idx + 1}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="right-panel">
            <h2>📊 Extracted Data</h2>
            {renderInvoiceData(summary)}
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
