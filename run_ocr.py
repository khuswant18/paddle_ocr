from paddleocr import PaddleOCR
import os
from pdf2image import convert_from_path
import tempfile

# Initialize PaddleOCR with determined working settings
ocr = PaddleOCR(lang='en', use_textline_orientation=False, use_doc_orientation_classify=False, use_doc_unwarping=False)

input_path = 'sample1.jpg' # Path to the image or PDF file for OCR
# Directory to save visualized OCR results from the predict API
output_dir = 'ocr_output_predict'
os.makedirs(output_dir, exist_ok=True) # Create output directory if it doesn't exist

# Function to check if file is PDF
def is_pdf(file_path):
    return file_path.lower().endswith('.pdf')

# Function to convert PDF to images
def pdf_to_images(pdf_path):
    return convert_from_path(pdf_path)

# Get list of images to process
temp_dir = None
if is_pdf(input_path):
    if not os.path.exists(input_path):
        print(f"Error: PDF file '{input_path}' does not exist.")
        exit(1)
    print(f"Converting PDF: {input_path} to images")
    try:
        images = pdf_to_images(input_path)
        temp_dir = tempfile.mkdtemp()
        image_paths = []
        for i, image in enumerate(images):
            img_path = os.path.join(temp_dir, f'page_{i+1}.jpg')
            image.save(img_path, 'JPEG')
            if os.path.exists(img_path):
                image_paths.append(img_path)
            else:
                print(f"Warning: Failed to save page {i+1}")
    except Exception as e:
        print(f"Error converting PDF: {e}")
        exit(1)
else:
    if not os.path.exists(input_path):
        print(f"Error: File '{input_path}' does not exist.")
        exit(1)
    image_paths = [input_path]

print(f"Performing OCR on: {input_path} using ocr.predict() API")
all_results = [] 
for img_path in image_paths:
    print(f"Processing: {os.path.basename(img_path)}")
    prediction_results = ocr.predict(img_path)
    if prediction_results:
        all_results.extend(prediction_results)

prediction_results = all_results

if prediction_results:
    print("\nOCR Prediction Results:")
    all_extracted_texts = []
    
    # Iterate through the list of OCRResult objects
    # (typically one item for a single image)
    for i, res_obj in enumerate(prediction_results):
        # Text extraction
        item_text = None
        # Text is found within res_obj.json['res']['rec_texts']
        if hasattr(res_obj, 'json') and isinstance(res_obj.json, dict):
            json_data = res_obj.json
            if 'res' in json_data and isinstance(json_data['res'], dict):
                res_content = json_data['res']
                if 'rec_texts' in res_content and isinstance(res_content['rec_texts'], list):
                    # Filter out empty strings and join the meaningful recognized texts
                    meaningful_texts = [text for text in res_content['rec_texts'] if isinstance(text, str) and text.strip()]
                    if meaningful_texts:
                        item_text = "\n".join(meaningful_texts)
        
        if item_text:
            all_extracted_texts.append(item_text)
        else:
            # If text is not extracted, print a warning and the raw result object for debugging
            print(f"Warning: Could not extract text for result item {i+1}.")
            if hasattr(res_obj, 'print'): # Print the raw result object if text extraction failed
                print(f"--- Raw result object {i+1} for debugging ---")
                res_obj.print()
                print(f"--- End of raw result object {i+1} ---")

        # Saving visualization
        if hasattr(res_obj, 'save_to_img'):
            try:
                # PaddleOCR typically generates the filename itself within the specified directory
                res_obj.save_to_img(output_dir)
                print(f"Visualization for item {i+1} saved to directory: {output_dir}")
            except Exception as e_save:
                print(f"Error saving visualization for item {i+1} to '{output_dir}': {e_save}")
        else:
            print(f"Result item {i+1} does not have 'save_to_img' method.")
        
    if all_extracted_texts:
        print("\n\nRecognized Text:")
        # Join text from all result items (usually one for a single image)
        print("\n---\n".join(all_extracted_texts))
    else:
        print("Could not extract text from OCR results (ocr.predict()).")

else: # This corresponds to `if prediction_results:`
    print("OCR (ocr.predict() API) returned no results or an empty result (initial check).")

# Cleanup temp directory if used
if temp_dir and os.path.exists(temp_dir):
    import shutil
    shutil.rmtree(temp_dir)
