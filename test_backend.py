#!/usr/bin/env python3
"""
Test script for the backend API
Tests both health check and file upload endpoints
"""
import requests
import sys
import time

BASE_URL = "http://localhost:5000"

def test_health():
    """Test health endpoint"""
    print("🔍 Testing health endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/api/health", timeout=5)
        if response.status_code == 200:
            print(f"✅ Health check passed: {response.json()}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_upload(file_path):
    """Test file upload endpoint"""
    print(f"\n📤 Testing upload with: {file_path}")
    try:
        with open(file_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(f"{BASE_URL}/api/upload", files=files, timeout=60)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Upload successful!")
            print(f"\n📊 Extracted Invoice Data:")
            print("-" * 60)
            
            invoice_data = data.get('invoice_data', {})
            if invoice_data:
                print(f"Invoice Number: {invoice_data.get('invoice_number', 'N/A')}")
                print(f"Invoice Date: {invoice_data.get('invoice_date', 'N/A')}")
                print(f"Seller: {invoice_data.get('seller_name', 'N/A')}")
                print(f"Buyer: {invoice_data.get('buyer_name', 'N/A')}")
                print(f"Grand Total: ₹{invoice_data.get('grand_total', '0.00')}")
                
                items = invoice_data.get('items', [])
                if items:
                    print(f"\nItems: {len(items)}")
                    for idx, item in enumerate(items[:3], 1):
                        print(f"  {idx}. {item.get('description', 'N/A')[:40]} - ₹{item.get('amount', '0')}")
                
                print("\n✨ Invoice extraction successful!")
                return True
            else:
                print("⚠️  No invoice data extracted")
                return False
        else:
            print(f"❌ Upload failed: {response.status_code}")
            print(f"Error: {response.json()}")
            return False
    except Exception as e:
        print(f"❌ Upload error: {e}")
        return False

def wait_for_backend(max_wait=60):
    """Wait for backend to be ready"""
    print("⏳ Waiting for backend to start...")
    for i in range(max_wait):
        try:
            response = requests.get(f"{BASE_URL}/api/health", timeout=2)
            if response.status_code == 200:
                print("✅ Backend is ready!")
                return True
        except:
            pass
        time.sleep(1)
        if i % 10 == 0 and i > 0:
            print(f"   Still waiting... ({i}s)")
    print("❌ Backend did not start in time")
    return False

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 Backend API Test Suite")
    print("=" * 60)
    
    # Wait for backend
    if not wait_for_backend():
        sys.exit(1)
    
    # Test health
    if not test_health():
        sys.exit(1)
    
    # Test upload with sample file
    sample_file = sys.argv[1] if len(sys.argv) > 1 else "sample1.jpg"
    if test_upload(sample_file):
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        sys.exit(0)
    else:
        print("\n" + "=" * 60)
        print("❌ SOME TESTS FAILED")
        print("=" * 60)
        sys.exit(1)
