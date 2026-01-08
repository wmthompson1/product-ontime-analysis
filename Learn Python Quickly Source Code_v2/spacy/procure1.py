import pytesseract
import cv2
import spacy
import re
import pandas as pd

# Load a pre-trained spaCy model (e.g., 'en_core_web_sm')
# You need to download it first using: python -m spacy download en_core_web_sm
nlp = spacy.load("en_core_web_sm")

def extract_data_from_invoice(image_path):
    # 1. Image Preprocessing with OpenCV
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # Further processing like thresholding can improve accuracy
    
    # 2. Text Extraction with OCR (Pytesseract)
    raw_text = pytesseract.image_to_string(gray)
    
    # 3. Data Extraction with NLP (spaCy) and Regex
    doc = nlp(raw_text)
    
    invoice_details = {}
    
    # Example: Extract invoice number using regex (common pattern)
    # This is a basic example; patterns vary by invoice type
    invoice_num_match = re.search(r"Invoice\s*Number[:#]?\s*(\w+)", raw_text, re.IGNORECASE)
    if invoice_num_match:
        invoice_details['Invoice Number'] = invoice_num_match.group(1)

    # Example: Extracting entities using spaCy's Named Entity Recognition (NER)
    for ent in doc.ents:
        if ent.label_ == "DATE" and not 'Date' in invoice_details:
            invoice_details['Date'] = ent.text
        elif ent.label_ == "ORG" and not 'Vendor' in invoice_details:
            invoice_details['Vendor'] = ent.text
            
    # More advanced NLP or custom logic is often needed for specific fields
            
    return invoice_details, raw_text

# Usage
image_file = "scanned_invoice.png"
details, text = extract_data_from_invoice(image_file)
print("Extracted Details:", details)
