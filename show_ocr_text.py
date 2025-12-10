#!/usr/bin/env python3
"""Show OCR text from image with line numbers."""

import sys
sys.path.insert(0, '/Users/khuswantrajpurohit/Documents/GitHub/ocr_screen')

from app.ocr_utils import OCRProcessor

if len(sys.argv) < 2:
    print("Usage: python show_ocr_text.py <image_path> [search_term]")
    sys.exit(1)

image_path = sys.argv[1]
search_term = sys.argv[2] if len(sys.argv) > 2 else None

print(f"\n🔍 OCR Text from: {image_path}")
print("=" * 70)

ocr = OCRProcessor(lang='en')
text = ocr.process_image(image_path)

if not text:
    print("❌ Failed to extract text from image")
    sys.exit(1)

lines = text.split('\n')

print(f"\nTotal lines extracted: {len(lines)}\n")

if search_term:
    print(f"\n🎯 Searching for: '{search_term}'")
    print("=" * 70)
    found = False
    for i, line in enumerate(lines, 1):
        if search_term.lower() in line.lower():
            found = True
            print(f"Line {i:3d}: {line}")
            # Show context (2 lines before and after)
            if i > 1:
                print(f"         (context above: {lines[i-2]})")
            if i < len(lines):
                print(f"         (context below: {lines[i]})")
            print()
    
    if not found:
        print(f"❌ '{search_term}' not found in OCR text")
else:
    # Show all lines
    for i, line in enumerate(lines, 1):
        if line.strip():  # Only show non-empty lines
            print(f"{i:3d}. {line}")

print("\n" + "=" * 70)
