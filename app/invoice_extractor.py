"""
Fast Invoice Data Extractor with Fuzzy Matching
Extracts all invoice details - uses fuzzy matching for keyword variations
No AI needed - fast and works offline
"""
import re
import json
import os
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from rapidfuzz import fuzz, process


@dataclass
class InvoiceItem:
    """Single line item."""
    sr_no: int = 0
    description: str = ""
    hsn_code: str = ""
    quantity: float = 0
    unit: str = ""
    unit_price: float = 0
    discount: float = 0
    tax_rate: float = 0
    amount: float = 0


@dataclass 
class InvoiceData:
    """Complete invoice data."""
    # Invoice Info
    invoice_number: str = ""
    invoice_date: str = ""
    due_date: str = ""
    po_number: str = ""
    
    # Seller/Sender
    seller_name: str = ""
    seller_address: str = ""
    seller_phone: str = ""
    seller_email: str = ""
    seller_gstin: str = ""
    seller_pan: str = ""
    
    # Buyer/Receiver
    buyer_name: str = ""
    buyer_address: str = ""
    buyer_phone: str = ""
    buyer_email: str = ""
    buyer_gstin: str = ""
    
    # Items
    items: List[InvoiceItem] = field(default_factory=list) 
    
    # Amounts
    subtotal: float = 0
    discount: float = 0
    cgst: float = 0
    sgst: float = 0
    igst: float = 0
    tax_total: float = 0
    shipping: float = 0
    grand_total: float = 0
    amount_paid: float = 0
    balance_due: float = 0
    
    # Extra
    payment_terms: str = ""
    bank_name: str = ""
    account_number: str = ""
    ifsc_code: str = ""
    notes: str = ""


class FuzzyMatcher:
    """Fast fuzzy matching for invoice keywords."""
    
    # Define keyword variations for each field
    KEYWORDS = {
        # Invoice identifiers - fuzzy matches inv, in, invoice, etc.
        'invoice_number': ['invoice', 'inv', 'in', 'invoice no', 'invoice number', 'inv no', 'inv#', 'invoice#', 'bill no', 'bill number', 'receipt no', 'receipt', 'voucher no', 'ref', 'reference', 'bill', 'memo'],
        'invoice_date': ['date', 'invoice date', 'inv date', 'bill date', 'dated', 'dt', 'issue date', 'doc date'],
        'due_date': ['due date', 'due', 'payment due', 'due by', 'pay by', 'due on', 'payable by'],
        'po_number': ['po', 'po no', 'purchase order', 'p.o', 'p.o.', 'order no', 'order number', 'order'],
        
        # Seller/Vendor
        'seller_name': ['from', 'seller', 'vendor', 'sold by', 'supplier', 'company', 'bill from', 'shipper'],
        'seller_gstin': ['gstin', 'gst no', 'gst', 'gst number', 'gstn', 'gst in', 'seller gstin', 'vendor gst'],
        'seller_pan': ['pan', 'pan no', 'pan number', 'pan card'],
        
        # Buyer/Customer  
        'buyer_name': ['to', 'bill to', 'billed to', 'sold to', 'buyer', 'customer', 'consignee', 'ship to', 'client', 'party'],
        'buyer_gstin': ['buyer gstin', 'customer gstin', 'party gstin'],
        
        # Item columns - fuzzy matches qty/qnty/quantity, amt/amount, etc.
        'description': ['description', 'desc', 'particulars', 'item', 'items', 'product', 'goods', 'service', 'details', 'name'],
        'quantity': ['qty', 'quantity', 'qnty', 'qnt', 'units', 'nos', 'no', 'pcs', 'q', 'qy'],
        'unit': ['unit', 'uom', 'u/m', 'un'],
        'unit_price': ['rate', 'price', 'unit price', 'unit rate', 'mrp', 'cost', 'per unit', 'rt', 'prc'],
        'hsn_code': ['hsn', 'hsn code', 'hsn/sac', 'sac', 'sac code'],
        'item_amount': ['amount', 'amt', 'total', 'value', 'line total', 'amnt', 'amout', 'ammount'],
        
        # Totals - fuzzy matches total/totl/ttl, amount/amt/amnt, etc.
        'subtotal': ['subtotal', 'sub total', 'sub-total', 'taxable value', 'taxable amount', 'net amount', 'basic amount', 'sub', 'subtot'],
        'discount': ['discount', 'disc', 'less', 'rebate', 'deduction', 'dis', 'dsc'],
        'cgst': ['cgst', 'central gst', 'central tax', 'c gst', 'c.gst'],
        'sgst': ['sgst', 'state gst', 'state tax', 's gst', 's.gst'],
        'igst': ['igst', 'integrated gst', 'integrated tax', 'i gst', 'i.gst'],
        'tax_total': ['tax', 'tax amount', 'total tax', 'gst amount', 'vat', 'tax amt'],
        'shipping': ['shipping', 'freight', 'delivery', 'transport', 'courier', 'handling', 'ship', 'frght'],
        'grand_total': ['total', 'grand total', 'total amount', 'amount due', 'net payable', 'invoice total', 
                        'final amount', 'gross total', 'payable', 'total due', 'tot', 'ttl', 'g total',
                        'amount', 'amt', 'total amt', 'net total', 'bill amount', 'invoice amount'],
        'amount_paid': ['paid', 'amount paid', 'received', 'payment received', 'advance', 'pd'],
        'balance_due': ['balance', 'balance due', 'due', 'outstanding', 'remaining', 'bal'],
        
        # Bank details
        'bank_name': ['bank', 'bank name', 'banker', 'bank details'],
        'account_number': ['account', 'a/c', 'ac no', 'account no', 'account number', 'acct', 'acc', 'a/c no'],
        'ifsc_code': ['ifsc', 'ifsc code', 'bank code', 'ifsc/neft'],
        
        # Other
        'payment_terms': ['terms', 'payment terms', 'credit', 'credit days', 'payment'],
    }
    
        #threshold=65 means 65% similarity is enough for a match
        #Creates a reverse lookup: {'invoice': 'invoice_number', 'inv': 'invoice_number', ...}
        #This allows O(1) exact match lookups before doing expensive fuzzy matching

    def __init__(self, threshold: int = 65):
        """
        Args:
            threshold: Minimum fuzzy match score (0-100). Lower = more lenient.
        """
        self.threshold = threshold
        # Pre-process keywords for faster matching
        self._all_keywords = {}
        for field_name, variations in self.KEYWORDS.items():
            for var in variations:
                self._all_keywords[var.lower()] = field_name
    
    def match_field(self, text: str) -> Optional[str]:
        """Find which field a text matches using fuzzy matching."""
        text_lower = text.lower().strip() 
        
        # Exact match first (fastest) 
        if text_lower in self._all_keywords:
            return self._all_keywords[text_lower]
        
        # Fuzzy match with multiple scorers for better results
        result = process.extractOne(
            text_lower, 
            self._all_keywords.keys(),
            scorer=fuzz.WRatio,  # Better for partial matches
            score_cutoff=self.threshold
        )
        
        if result:
            matched_keyword, score, _ = result
            return self._all_keywords[matched_keyword]
        
        return None
    
    def is_match(self, text: str, field: str, threshold: int = None) -> bool:
        """Check if text matches a specific field."""
        threshold = threshold or self.threshold
        keywords = self.KEYWORDS.get(field, [])
        text_lower = text.lower().strip()
        
        for keyword in keywords:
            # Exact match
            if keyword in text_lower:
                return True
            # Fuzzy match
            score = fuzz.WRatio(text_lower, keyword)
            if score >= threshold:
                return True
        
        return False
    
    def find_field_value(self, text: str, field: str) -> Optional[str]:
        """Find value for a specific field in text using fuzzy matching."""
        keywords = self.KEYWORDS.get(field, [])
        text_lower = text.lower()
        
        for keyword in keywords:
            # Pattern: keyword followed by separator then value
            patterns = [
                rf'{re.escape(keyword)}[\s:.\-]*[:\s]+([^\n]+)',
                rf'{re.escape(keyword)}[\s]*[:.\-=]+[\s]*([^\n]+)',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text_lower)
                if match:
                    value = match.group(1).strip()
                    if value and len(value) > 0:
                        return value
        
        return None


class FastInvoiceExtractor:
    """
    Fast invoice extractor with fuzzy matching.
    No AI needed - extracts all common invoice fields.
    """
    
    def __init__(self, fuzzy_threshold: int = 65):
        self.matcher = FuzzyMatcher(threshold=fuzzy_threshold)
        
        # Compiled regex patterns for speed
        self.patterns = {
            'amount': re.compile(r'[\$₹€£]?\s*(\d{1,3}(?:[,\s]?\d{2,3})*(?:\.\d{1,2})?)'),
            'date': re.compile(r'(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4}|\d{1,2}\s*(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*[\s,]*\d{2,4})', re.I),
            'phone': re.compile(r'(?:\+\d{1,3}[-.\s]?)?(?:\(?\d{2,5}\)?[-.\s]?)?\d{3,5}[-.\s]?\d{4,5}'),
            'email': re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'),
            'gstin': re.compile(r'\d{2}[A-Z]{5}\d{4}[A-Z][A-Z\d]Z[A-Z\d]'),
            'pan': re.compile(r'[A-Z]{5}\d{4}[A-Z]'),
            'ifsc': re.compile(r'[A-Z]{4}0[A-Z0-9]{6}'),
            'account': re.compile(r'\d{9,18}'),
        } 
    
    def extract(self, ocr_text: str) -> InvoiceData:
        """Extract all invoice data from OCR text."""
        invoice = InvoiceData()
        lines = [l.strip() for l in ocr_text.split('\n') if l.strip()]
        text_upper = ocr_text.upper()
        
        # Extract basic fields using fuzzy matching
        invoice.invoice_number = self._extract_invoice_number(ocr_text, lines)
        invoice.invoice_date = self._extract_date(ocr_text, 'invoice_date')
        invoice.due_date = self._extract_date(ocr_text, 'due_date')
        invoice.po_number = self._extract_po_number(ocr_text)
        
        # Extract parties
        self._extract_parties(lines, invoice)
        
        # Extract contact info
        self._extract_contacts(ocr_text, invoice)
        
        # Extract tax IDs
        self._extract_tax_ids(text_upper, invoice)
        
        # Extract items - most important!
        invoice.items = self._extract_items(lines, ocr_text)
        
        # Validate and fix item amounts
        self._validate_items(invoice)
        
        # Extract amounts
        self._extract_amounts(ocr_text, invoice)
        
        # Validate totals against item sum
        self._validate_totals(invoice)
        
        # Extract bank details
        self._extract_bank_details(ocr_text, text_upper, invoice)
        
        return invoice
    
    def _validate_items(self, invoice: InvoiceData):
        """Validate and fix item calculations: qty × rate should equal amount."""
        for item in invoice.items:
            if item.quantity > 0 and item.unit_price > 0:
                calculated_amount = item.quantity * item.unit_price
                if abs(calculated_amount - item.amount) > 0.01:
                    item.amount = round(calculated_amount, 2)
    
    def _validate_totals(self, invoice: InvoiceData):
        """Validate that totals match item sums and fix discrepancies."""
        if not invoice.items:
            return
        
        # Calculate actual sum of items
        items_sum = sum(item.amount for item in invoice.items)
        
        # If subtotal is way off, recalculate
        if invoice.subtotal > 0:
            if abs(invoice.subtotal - items_sum) / items_sum > 0.1 if items_sum > 0 else True:
                # Subtotal seems wrong, might be OCR error
                pass  # Keep original but note it's suspicious
        
        # If grand_total seems wrong (way smaller than items sum), recalculate
        if invoice.grand_total > 0 and items_sum > 0:
            # Grand total should be >= items_sum (before discounts) or close to it
            if invoice.grand_total < items_sum * 0.5:  # Way too small
                # Likely OCR error - recalculate
                invoice.grand_total = items_sum - invoice.discount if invoice.discount else items_sum
        elif items_sum > 0 and invoice.grand_total == 0:
            # No grand total extracted - calculate from items
            invoice.grand_total = items_sum - invoice.discount if invoice.discount else items_sum
        
        # Update subtotal if missing
        if invoice.subtotal == 0 and items_sum > 0:
            invoice.subtotal = items_sum
    
    def _extract_invoice_number(self, text: str, lines: List[str]) -> str:
        """Extract invoice number using fuzzy matching."""
        
        # Invalid patterns - these are NOT invoice numbers
        invalid_patterns = [
            r'^\d{4}[a-z]+$',  # Address-like: 2525Narra
            r'^\d+\s+\w+\s+(extension|street|road|ave|avenue|blvd|city|subdivision)',  # Address
            r'^tel\.?\s*no',  # Phone reference
            r'^\d{3}[-.]\d{3}[-.]\d{4}',  # Phone number
            r'^\d{2}[-/]\d{2}[-/]\d{2,4}$',  # Date
        ]
        
        # Keywords that might mean invoice number
        inv_keywords = ['invoice', 'inv', 'bill no', 'bill number', 'receipt no', 'receipt', 
                        'voucher no', 'ref no', 'reference', 'memo no', 'doc no', 'document'] 
        
        for keyword in inv_keywords:
            patterns = [
                rf'{keyword}[\s#.:no-]*[:\s#]+([A-Z0-9\-/]+)',
                rf'{keyword}[\s]*(?:no|number|#|num)?[\s.:]*([A-Z0-9\-/]+)',
            ]
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    val = match.group(1).strip()
                    # Validate the invoice number
                    if len(val) >= 2 and len(val) <= 30:
                        val_lower = val.lower()
                        # Skip common non-invoice words
                        if val_lower in ['no', 'number', 'date', 'to', 'the', 'from', 'for']:
                            continue
                        # Check against invalid patterns
                        is_invalid = False
                        for inv_pattern in invalid_patterns:
                            if re.search(inv_pattern, val, re.IGNORECASE):
                                is_invalid = True
                                break
                        if not is_invalid:
                            # Should have at least one digit for invoice number
                            if re.search(r'\d', val):
                                return val
        
        # Look for № or # followed by number
        match = re.search(r'[№#]\s*(\d{4,})', text)
        if match:
            return match.group(1)
        
        return ""
    
    def _extract_po_number(self, text: str) -> str:
        """Extract PO number."""
        patterns = [
            r'p\.?\s*o\.?\s*n?o?[\s.:]*([A-Z0-9\-]+)',
            r'purchase\s*order[\s.:]*([A-Z0-9\-]+)',
            r'order[\s#.:no]*[:\s]+([A-Z0-9\-]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return ""
    
    def _extract_date(self, text: str, field: str) -> str:
        """Extract date for a specific field."""
        
        # More specific date patterns
        date_patterns = [
            # DD/MM/YYYY or MM/DD/YYYY or DD-MM-YYYY
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            # YYYY/MM/DD or YYYY-MM-DD
            r'(\d{4}[/-]\d{1,2}[/-]\d{1,2})',
            # DD Month YYYY or Month DD, YYYY
            r'(\d{1,2}\s*(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*[\s,]*\d{2,4})',
            r'((?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2}[,\s]+\d{2,4})',
        ]
        
        # Keywords for this field type
        field_keywords = self.matcher.KEYWORDS.get(field, [])
        
        # Search near the field keyword first
        for keyword in field_keywords:
            # Look for keyword followed by date
            for date_pattern in date_patterns:
                pattern = rf'{re.escape(keyword)}[^\n]*?{date_pattern}'
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    date_str = match.group(1)
                    # Validate it's not a phone number (phone numbers have 10+ consecutive digits)
                    digits_only = re.sub(r'\D', '', date_str)
                    if len(digits_only) <= 8:  # Valid date shouldn't have more than 8 digits
                        return date_str
        
        # For invoice date, find first valid date in document (not in phone context)
        if field == 'invoice_date':
            for date_pattern in date_patterns:
                matches = re.finditer(date_pattern, text, re.IGNORECASE)
                for match in matches:
                    date_str = match.group(1)
                    # Check context - skip if near 'tel', 'phone', 'fax'
                    start = max(0, match.start() - 20)
                    context = text[start:match.start()].lower()
                    if not any(word in context for word in ['tel', 'phone', 'fax', 'mobile', 'cell']):
                        digits_only = re.sub(r'\D', '', date_str)
                        if len(digits_only) <= 8:
                            return date_str
        
        return ""
    
    def _extract_parties(self, lines: List[str], invoice: InvoiceData):
        """Extract seller and buyer information."""
        
        # Markers for different sections   
        seller_markers = ['from:', 'seller:', 'vendor:', 'sold by:', 'supplier:', 'bill from:', 'shipper:']
        buyer_markers = ['to:', 'bill to:', 'billed to:', 'sold to:', 'buyer:', 'customer:', 'ship to:', 'consignee:', 'deliver to:']
        end_markers = ['description', 'qty', 'quantity', 'unit', 'amount', 'rate', 'price', 'hsn', 'item', 'particulars', 'sl.', 'sr.', 'no.']
        
        # Skip patterns - these are not company names
        skip_patterns = [
            r'^\d{2,4}[-/]\d{2}[-/]\d{2,4}$',  # Dates
            r'^\d{3}[-.\s]\d{3}[-.\s]\d{4}',    # Phone numbers
            r'^tel\.?\s*no',                     # Tel labels
            r'^\d{2,}-\d{3}-\d{3}',             # Tax numbers like TIN
            r'^(invoice|bill|receipt|date|po|order)',  # Document labels
            r'^(gstin|pan|tin|vat)',             # Tax ID labels
            r'^[\d,\.]+$',                       # Pure numbers
            r'^\d+\s*(pcs|box|kg|nos|units)',   # Quantity lines
        ]
        
        current_section = None
        seller_lines = []
        buyer_lines = []
        header_lines = []
        
        def is_valid_party_line(line: str) -> bool:
            """Check if line could be part of party info (name/address)."""
            line_lower = line.lower().strip()
            
            # Skip if matches any skip pattern
            for pattern in skip_patterns:
                if re.search(pattern, line_lower, re.I):
                    return False
            
            # Should have some letters (not just numbers/symbols)
            if not re.search(r'[a-zA-Z]{2,}', line):
                return False
            
            # Skip very short lines
            if len(line.strip()) < 3:
                return False
                
            return True
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            if not line_stripped:
                continue
            
            line_lower = line_stripped.lower()
            
            # Skip if we hit the item table
            if any(m in line_lower for m in end_markers):
                break
            
            # Skip product codes
            if re.search(r'\bHY[\s(]?\d+', line_stripped, re.I):
                continue
            
            # Check for "SOLD TO" marker (buyer section)
            if 'sold to' in line_lower:
                current_section = 'buyer'
                # Get text after marker
                idx = line_lower.find('sold to')
                remainder = line_stripped[idx + 7:].strip(' :.-')
                if remainder and len(remainder) > 2 and is_valid_party_line(remainder):
                    buyer_lines.append(remainder)
                continue
            
            # Check for other buyer markers
            found_marker = False
            for m in buyer_markers:
                m_clean = m.rstrip(':')
                if m_clean in line_lower:
                    current_section = 'buyer'
                    idx = line_lower.find(m_clean) + len(m_clean)
                    remainder = line_stripped[idx:].strip(' :.-')
                    if remainder and len(remainder) > 2 and is_valid_party_line(remainder):
                        buyer_lines.append(remainder)
                    found_marker = True
                    break
            if found_marker:
                continue
            
            # Check for seller markers
            for m in seller_markers:
                m_clean = m.rstrip(':')
                if m_clean in line_lower:
                    current_section = 'seller'
                    idx = line_lower.find(m_clean) + len(m_clean)
                    remainder = line_stripped[idx:].strip(' :.-')
                    if remainder and len(remainder) > 2 and is_valid_party_line(remainder):
                        seller_lines.append(remainder)
                    found_marker = True
                    break
            if found_marker:
                continue
            
            # First few lines are usually company header (seller)
            if i < 8 and not current_section:
                # Look for company-like names
                if is_valid_party_line(line_stripped):
                    if (any(ind in line_lower for ind in ['inc', 'ltd', 'llc', 'pvt', 'corp', 'marketing', 'enterprise', 'trading', 'company', 'industries']) or
                        (len(line_stripped) > 5 and not any(skip in line_lower for skip in ['invoice', 'date', 'tel', 'fax', 'address', 'tin', 'vat', 'gstin']))):
                        header_lines.append(line_stripped)
            
            # Add to current section if valid
            if current_section == 'seller' and len(seller_lines) < 5:
                if is_valid_party_line(line_stripped):
                    if not any(skip in line_lower for skip in ['tel', 'fax', 'phone', 'email', 'tin', 'vat', 'date', 'invoice', 'gstin']):
                        seller_lines.append(line_stripped)
            elif current_section == 'buyer' and len(buyer_lines) < 5:
                if is_valid_party_line(line_stripped):
                    if not any(skip in line_lower for skip in ['tel', 'fax', 'phone', 'email', 'tin', 'vat', 'date', 'invoice', 'terms', 'osca', 'salesman', 'cardholder', 'gstin']):
                        buyer_lines.append(line_stripped)
        
        # Use header as seller if no explicit seller found
        if not seller_lines and header_lines:
            seller_lines = header_lines[:4]
        
        # Clean up and assign extracted data
        if seller_lines:
            # First line should be company name
            invoice.seller_name = seller_lines[0]
            if len(seller_lines) > 1:
                # Join remaining lines as address, filtering out duplicates
                addr_lines = [l for l in seller_lines[1:4] if l.lower() != seller_lines[0].lower()]
                invoice.seller_address = ', '.join(addr_lines)
        
        if buyer_lines:
            invoice.buyer_name = buyer_lines[0]
            if len(buyer_lines) > 1:
                addr_lines = [l for l in buyer_lines[1:4] if l.lower() != buyer_lines[0].lower()]
                invoice.buyer_address = ', '.join(addr_lines)
    
    def _extract_contacts(self, text: str, invoice: InvoiceData):
        """Extract phone numbers and emails."""
        
        phones = self.patterns['phone'].findall(text)
        phones = [p for p in phones if len(re.sub(r'\D', '', p)) >= 10]
        
        if phones:
            invoice.seller_phone = phones[0]
            if len(phones) > 1:
                invoice.buyer_phone = phones[1]
        
        emails = self.patterns['email'].findall(text)
        if emails:
            invoice.seller_email = emails[0]
            if len(emails) > 1:
                invoice.buyer_email = emails[1]
    
    def _extract_tax_ids(self, text_upper: str, invoice: InvoiceData):
        """Extract GSTIN, PAN, etc."""
        
        gstins = self.patterns['gstin'].findall(text_upper)
        if gstins:
            invoice.seller_gstin = gstins[0]
            if len(gstins) > 1:
                invoice.buyer_gstin = gstins[1]
        
        pans = self.patterns['pan'].findall(text_upper)
        if pans:
            pans = [p for p in pans if p not in ''.join(gstins)]
            if pans:
                invoice.seller_pan = pans[0]
    
    def _extract_items(self, lines: List[str], full_text: str) -> List[InvoiceItem]:
        """Extract all line items from invoice using fuzzy matching."""
        items = []
        
        # First, try multicolumn extraction (when OCR reads columns separately)
        # This is common for tabular invoices
        multicolumn_items = self._extract_items_multicolumn(lines)
        if len(multicolumn_items) >= 2:  # If we got at least 2 items from multicolumn
            return multicolumn_items
        
        # Multiple patterns to catch different formats
        item_patterns = [
            # QTY UNIT DESCRIPTION RATE AMOUNT
            re.compile(r'^(\d+)\s+(cs|pcs?|box|kg|nos?|units?|ltrs?|ml|gms?|bags?|btls?|doz|ea)\s+(.+?)\s+(\d[\d,]*\.?\d*)\s+(\d[\d,]*\.?\d*)\s*$', re.I),
            # SR DESCRIPTION QTY RATE AMOUNT  
            re.compile(r'^(\d{1,3})\s+(.+?)\s+(\d+(?:\.\d+)?)\s+(\d[\d,]*\.?\d*)\s+(\d[\d,]*\.?\d*)\s*$'),
            # HY/SKU (CODE) PRODUCT QTY RATE AMOUNT - common invoice format
            re.compile(r'^([A-Z]{2,4}[\s(]?\d+[A-Z]*[\)]?)\s+(.+?)\s+(\d+(?:\.\d+)?)\s+(\d[\d,]*\.?\d*)\s+(\d[\d,]*\.?\d*)\s*$', re.I),
        ]
        
        # Skip these lines (fuzzy matched)
        skip_keywords = ['total', 'subtotal', 'amount', 'tax', 'gst', 'discount', 'shipping', 
                        'grand', 'balance', 'paid', 'due', 'net', 'gross', 'less', 'add',
                        'description', 'qty', 'rate', 'unit', 'particular', 'hsn', 'sac',
                        'vat', 'cgst', 'sgst', 'igst', 'invoice', 'bill', 'date', 'address',
                        'phone', 'tel', 'fax', 'email', 'from', 'buyer', 'seller', 'vendor',
                        'customer', 'ship', 'print', 'page', 'authority', 'tin', 'accredit']
        
        sr_no = 0
        processed_descriptions = set()
        
        for line in lines:
            line = line.strip()
            if not line or len(line) < 5:
                continue
            
            line_lower = line.lower()
            
            # Skip header/total/metadata lines using fuzzy match
            is_skip = False
            for kw in skip_keywords:
                if kw in line_lower and len(line) < 60:
                    # But don't skip if it looks like a product (has HY code or similar)
                    if not re.search(r'\bHY[\s(]?\d+', line, re.I):
                        is_skip = True
                        break
            
            if is_skip:
                continue
            
            # Try each pattern
            matched = False
            for pattern in item_patterns:
                match = pattern.match(line)
                if match:
                    groups = match.groups()
                    try:
                        sr_no += 1
                        
                        if len(groups) == 5 and groups[1].lower() in ['cs', 'pcs', 'pc', 'box', 'kg', 'nos', 'no', 'unit', 'units', 'ltr', 'ml', 'gm', 'bag', 'btl', 'doz', 'ea']:
                            # QTY UNIT DESC RATE AMT format
                            item = InvoiceItem(
                                sr_no=sr_no,
                                quantity=float(groups[0]),
                                unit=groups[1].upper(),
                                description=groups[2].strip(),
                                unit_price=float(groups[3].replace(',', '')),
                                amount=float(groups[4].replace(',', ''))
                            )
                        elif len(groups) == 5 and groups[0].upper().startswith(('HY', 'SK', 'PR')):
                            # SKU DESC QTY RATE AMT format
                            item = InvoiceItem(
                                sr_no=sr_no,
                                description=f"{groups[0]} {groups[1]}".strip(),
                                quantity=float(groups[2]),
                                unit_price=float(groups[3].replace(',', '')),
                                amount=float(groups[4].replace(',', ''))
                            )
                        elif len(groups) == 5:
                            # SR DESC QTY RATE AMT format
                            item = InvoiceItem(
                                sr_no=int(groups[0]),
                                description=groups[1].strip(),
                                quantity=float(groups[2]),
                                unit_price=float(groups[3].replace(',', '')),
                                amount=float(groups[4].replace(',', ''))
                            )
                        else:
                            # DESC QTY RATE AMT format
                            item = InvoiceItem(
                                sr_no=sr_no,
                                description=groups[0].strip(),
                                quantity=float(groups[1]),
                                unit_price=float(groups[2].replace(',', '')),
                                amount=float(groups[3].replace(',', ''))
                            )
                        
                        # Check for duplicate
                        desc_key = item.description[:20].lower()
                        if item.amount > 0 and item.description and desc_key not in processed_descriptions:
                            items.append(item)
                            processed_descriptions.add(desc_key)
                            matched = True
                        break
                    except (ValueError, IndexError):
                        continue
            
            # Fallback: Look for product code patterns (HY, SKU, etc.)
            if not matched:
                # Match HY codes specifically  
                if re.search(r'\bHY[\s(]?\d+', line, re.I):
                    item = self._parse_hy_product_line(line, sr_no + 1)
                    if item:
                        desc_key = item.description[:20].lower()
                        if desc_key not in processed_descriptions:
                            sr_no += 1
                            items.append(item)
                            processed_descriptions.add(desc_key)
                elif re.search(r'\([A-Z0-9]+\)', line) or re.search(r'[A-Z]{2,4}[-\s]?\d{3,}', line):
                    item = self._parse_product_line(line, sr_no + 1)
                    if item:
                        desc_key = item.description[:20].lower()
                        if desc_key not in processed_descriptions:
                            sr_no += 1
                            items.append(item)
                            processed_descriptions.add(desc_key)
        
        # If multicolumn gave some results but standard gave none, use multicolumn
        if not items and multicolumn_items:
            return multicolumn_items
        
        return items
    
    def _parse_hy_product_line(self, line: str, sr_no: int) -> Optional[InvoiceItem]:
        """Parse HY product lines (e.g., 'HY(302) Star Jelly Candy 120g 1x40x24s 2 990.00 1,980.00')."""
        
        # Pattern: HY(CODE) PRODUCT_NAME PACK_FORMAT QTY RATE AMOUNT
        # The pack format like 1x40x24s is part of description, not quantity
        
        # Extract amounts from end (usually last 2-3 numbers are rate and amount)
        amounts = re.findall(r'(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?)', line)
        if len(amounts) < 2:
            return None
        
        try:
            # Filter to get actual monetary amounts (not small numbers like qty)
            float_amounts = [(i, float(a.replace(',', ''))) for i, a in enumerate(amounts)]
            
            # Separate potential quantities (small integers) from monetary amounts
            potential_qtys = [(i, v) for i, v in float_amounts if v < 200 and v == int(v)]
            monetary_amounts = [(i, v) for i, v in float_amounts if v >= 100]
            
            # If we have at least 2 monetary amounts, use them for rate and total
            if len(monetary_amounts) >= 2:
                monetary_sorted = sorted(monetary_amounts, key=lambda x: x[1])
                
                # Try to find rate and amount that satisfy qty × rate = amount
                best_match = None
                best_error = float('inf')
                
                for rate_idx, rate in monetary_sorted[:-1]:  # Skip largest as potential rate
                    for amt_idx, amount in monetary_sorted:
                        if amount <= rate:
                            continue
                        # Calculate quantity
                        calc_qty = amount / rate
                        rounded_qty = round(calc_qty)
                        
                        if 1 <= rounded_qty <= 200:
                            # Verify: qty × rate should equal amount exactly (or very close)
                            expected_amount = rounded_qty * rate
                            error = abs(expected_amount - amount)
                            
                            if error < best_error and error < 1:  # Allow small rounding error
                                best_error = error
                                best_match = (rounded_qty, rate, expected_amount)
                
                if best_match:
                    qty, rate, amount = best_match
                else:
                    # Fallback: largest is amount, second largest is rate
                    amount = monetary_sorted[-1][1]
                    rate = monetary_sorted[-2][1] if len(monetary_sorted) > 1 else amount
                    qty = round(amount / rate) if rate > 0 else 1
            else:
                # Fewer monetary amounts - use simple logic
                float_amounts_sorted = sorted(float_amounts, key=lambda x: x[1], reverse=True)
                amount = float_amounts_sorted[0][1] if float_amounts_sorted else 0
                rate = float_amounts_sorted[1][1] if len(float_amounts_sorted) > 1 else amount
                qty = 1
                
                # Try to find quantity from small numbers
                for idx, val in potential_qtys:
                    if val >= 1:
                        # Verify this qty makes sense
                        if rate > 0:
                            expected = val * rate
                            if abs(expected - amount) < 1:  # Matches
                                qty = int(val)
                                break
            
            # Extract description (everything up to the numbers at the end)
            desc = line
            # Remove the last 2-3 number groups that are likely rate/amount
            for _ in range(3):
                desc = re.sub(r'\s+\d[\d,]*\.?\d*\s*$', '', desc)
            desc = desc.strip()
            
            # Validate: qty × rate should equal amount (recalculate amount if needed)
            calculated_amount = qty * rate
            if abs(calculated_amount - amount) > 1:
                # The OCR'd amount might be wrong, use calculated
                amount = calculated_amount
            
            if amount > 0 and len(desc) > 3:
                return InvoiceItem(
                    sr_no=sr_no,
                    description=desc,
                    quantity=qty,
                    unit="",
                    unit_price=rate,
                    amount=amount
                )
        except ValueError:
            pass
        
        return None

    def _extract_items_multicolumn(self, lines: List[str]) -> List[InvoiceItem]:
        """
        Extract items when OCR detects columns separately.
        Strategy: Find price-amount pairs and calculate qty = amount / price
        """
        items = []
        
        # Product patterns
        product_patterns = [
            r'\bHY[\s({]?\d+',           # HY(302), HY 302, HY{302}
            r'\bHY\s*\([A-Z]?\d+',       # HY (600A), HY(A321)
        ]
        
        product_keywords = ['candy', 'jelly', 'chocolate', 'flavor', 
                           'biscuit', 'gum', 'powder', 'fruit', 'roll', 'stick', 
                           'cup', 'pop', 'bubble', 'yogurt', 'mango', 'orange', 
                           'strawberry', 'milk', 'cola', 'sofee', 'asstd']
        
        # Find where totals section starts
        totals_start_idx = len(lines)
        totals_keywords = ['total sales', 'grand total', 'total amount', 'less:', 
                          'vatable', 'vat-exempt', 'sales gross', 'received the above',
                          'thank you', 'remarks']
        for i, line in enumerate(lines):
            line_lower = line.lower()
            if any(kw in line_lower for kw in totals_keywords):
                totals_start_idx = i
                break
        
        # Collect products and monetary values
        product_info = []  # (line_idx, description)
        monetary_values = []  # (line_idx, value)
        
        for i, line in enumerate(lines):
            if i >= totals_start_idx:
                break
                
            line = line.strip()
            if not line:
                continue
            
            line_lower = line.lower()
            
            # Skip headers and metadata
            skip_words = ['total', 'subtotal', 'quantity', 'description', 'unit', 
                         'amount', 'signature', 'date:', 'sold to', 'terms',
                         'unitprice', 'remarks', 'vatable', 'vat-exempt', 'less:',
                         'add:', 'tin:', 'address', 'business', 'cardholder']
            if any(kw in line_lower for kw in skip_words):
                continue
            
            # Check if line is a product description
            is_product = any(re.search(p, line, re.I) for p in product_patterns)
            if not is_product and len(line) > 15:
                if any(word in line_lower for word in product_keywords):
                    is_product = True
            
            if is_product:
                product_info.append((i, line))
            # Pure number line - potential price or amount
            elif re.match(r'^[\d,\.]+$', line):
                try:
                    clean = line.replace(',', '')
                    # Handle format like 1.940.00 (European thousands separator)
                    if clean.count('.') > 1:
                        parts = clean.split('.')
                        # If last part is 2 digits, it's decimals
                        if len(parts[-1]) == 2:
                            clean = ''.join(parts[:-1]) + '.' + parts[-1]
                        else:
                            clean = ''.join(parts)
                    
                    val = float(clean)
                    if val >= 100:  # Only consider values >= 100 as prices/amounts
                        monetary_values.append((i, val))
                except ValueError:
                    pass
        
        # Find price-amount pairs (consecutive monetary values where amount >= price)
        # In invoices, typically: unit_price is followed by total_amount
        price_amount_pairs = []  # (price_idx, price, amount_idx, amount)
        
        used_values = set()
        for i in range(len(monetary_values) - 1):
            idx1, val1 = monetary_values[i]
            idx2, val2 = monetary_values[i + 1]
            
            if idx1 in used_values or idx2 in used_values:
                continue
            
            # Check if they're close together (within 3 lines)
            if abs(idx2 - idx1) <= 3:
                # Determine which is price and which is amount
                # Amount should be >= price (qty >= 1)
                if val2 >= val1:
                    price, amount = val1, val2
                    price_idx, amount_idx = idx1, idx2
                else:
                    price, amount = val2, val1
                    price_idx, amount_idx = idx2, idx1
                
                # Calculate quantity
                if price > 0:
                    calc_qty = amount / price
                    rounded_qty = round(calc_qty)
                    
                    # Verify it's a clean division (qty should be integer)
                    if rounded_qty >= 1 and rounded_qty <= 100:
                        error = abs(calc_qty - rounded_qty)
                        if error < 0.01:  # Nearly exact integer
                            price_amount_pairs.append((price_idx, price, amount_idx, amount, rounded_qty))
                            used_values.add(idx1)
                            used_values.add(idx2)
        
        # Match products to their price-amount pairs
        # Strategy: Sequential matching - pairs and products appear in same order
        # This works because OCR reads columns top-to-bottom, so first pair = first product
        
        # Sort products by line index (should already be in order, but ensure it)
        product_info_sorted = sorted(product_info, key=lambda x: x[0])
        # Price-amount pairs are already in order by line index
        
        # If counts match or are close, do direct sequential assignment
        if len(price_amount_pairs) >= len(product_info_sorted):
            # Direct sequential match: product N gets pair N
            for i, (prod_idx, description) in enumerate(product_info_sorted):
                if i < len(price_amount_pairs):
                    price_idx, price, amount_idx, amount, qty = price_amount_pairs[i]
                    items.append(InvoiceItem(
                        sr_no=len(items) + 1,
                        description=description,
                        quantity=qty,
                        unit="",
                        unit_price=price,
                        amount=amount
                    ))
                else:
                    # No pair available, add product with qty=1 and no price
                    items.append(InvoiceItem(
                        sr_no=len(items) + 1,
                        description=description,
                        quantity=1,
                        unit="",
                        unit_price=0,
                        amount=0
                    ))
        else:
            # Fewer pairs than products - fall back to nearest matching
            used_pairs = set()
            
            for prod_idx, description in product_info_sorted:
                best_pair = None
                best_distance = float('inf')
                
                for i, (price_idx, price, amount_idx, amount, qty) in enumerate(price_amount_pairs):
                    if i in used_pairs:
                        continue
                    
                    # Calculate distance from product to pair
                    dist_to_price = abs(prod_idx - price_idx)
                    dist_to_amount = abs(prod_idx - amount_idx)
                    dist = min(dist_to_price, dist_to_amount)
                    
                    # Prefer pairs that come before the product (common in column OCR)
                    if price_idx < prod_idx and amount_idx < prod_idx:
                        dist -= 1  # Stronger preference for pairs before
                    
                    if dist < best_distance and dist <= 10:
                        best_distance = dist
                        best_pair = (i, price, amount, qty)
                
                if best_pair:
                    pair_idx, price, amount, qty = best_pair
                    used_pairs.add(pair_idx)
                    
                    items.append(InvoiceItem(
                        sr_no=len(items) + 1,
                        description=description,
                        quantity=qty,
                        unit="",
                        unit_price=price,
                        amount=amount
                    ))
                else:
                    # No pair found - try to find any nearby amount
                    for amt_idx, amt_val in monetary_values:
                        if amt_idx not in used_values:
                            dist = abs(prod_idx - amt_idx)
                            if dist <= 5:
                                items.append(InvoiceItem(
                                    sr_no=len(items) + 1,
                                    description=description,
                                    quantity=1,
                                    unit="",
                                    unit_price=amt_val,
                                    amount=amt_val
                                ))
                                used_values.add(amt_idx)
                                break
                            break
        
        return items
    
    def _parse_product_line(self, line: str, sr_no: int) -> Optional[InvoiceItem]:
        """Parse a product line with flexible format."""
        
        # Extract all numbers from the line
        numbers = re.findall(r'(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?)', line)
        numbers = [n.replace(',', '') for n in numbers]
        
        if len(numbers) < 2:
            return None
        
        try:
            # Filter out small numbers that might be part of product code
            amounts = [float(n) for n in numbers if float(n) >= 10]
            
            if len(amounts) < 1:
                return None
            
            # Usually: last amount is total, second to last is rate
            amount = amounts[-1]
            rate = amounts[-2] if len(amounts) > 1 else amount
            
            # Look for quantity at start
            qty_match = re.match(r'^(\d+)\s+', line)
            qty = float(qty_match.group(1)) if qty_match and float(qty_match.group(1)) < 1000 else 1
            
            # Extract description (remove numbers from end)
            desc = line
            for _ in range(3):
                desc = re.sub(r'\s+\d[\d,]*\.?\d*\s*$', '', desc)
            desc = desc.strip()
            
            # Extract unit
            unit_match = re.search(r'\b(cs|pcs?|box|kg|nos?|units?|ea)\b', desc, re.I)
            unit = unit_match.group(1).upper() if unit_match else ""
            
            # Remove quantity and unit from start of description
            if qty > 1:
                desc = re.sub(r'^\d+\s+(?:cs|pcs?|box|kg|nos?|units?|ea)?\s*', '', desc, flags=re.I)
            
            if amount > 0 and len(desc) > 3:
                return InvoiceItem(
                    sr_no=sr_no,
                    description=desc.strip(),
                    quantity=qty,
                    unit=unit,
                    unit_price=rate,
                    amount=amount
                )
        except ValueError:
            pass
        
        return None
    
    def _extract_amounts(self, text: str, invoice: InvoiceData):
        """Extract all amounts using fuzzy matching."""
        
        text_lower = text.lower()
        
        # Amount fields to extract
        amount_fields = [
            ('subtotal', 'subtotal'),
            ('discount', 'discount'),
            ('cgst', 'cgst'),
            ('sgst', 'sgst'),
            ('igst', 'igst'),
            ('tax_total', 'tax_total'),
            ('shipping', 'shipping'),
            ('grand_total', 'grand_total'),
            ('amount_paid', 'amount_paid'),
            ('balance_due', 'balance_due'),
        ]
        
        for attr_name, field_name in amount_fields:
            keywords = self.matcher.KEYWORDS.get(field_name, [])
            
            for keyword in keywords:
                # Find keyword and extract following amount (fuzzy)
                # Allow for variations in spacing and separators
                pattern = rf'{re.escape(keyword)}[^0-9₹$]*[₹$Rs.\s]*(\d{{1,3}}(?:[,\s]?\d{{2,3}})*(?:\.\d{{1,2}})?)'
                match = re.search(pattern, text_lower)
                
                if match:
                    try:
                        amount = float(match.group(1).replace(',', '').replace(' ', ''))
                        current = getattr(invoice, attr_name)
                        if current == 0:  # Don't overwrite
                            setattr(invoice, attr_name, amount)
                        break
                    except ValueError:
                        continue
        
        # If no grand total found, look for largest reasonable amount
        if invoice.grand_total == 0:
            amounts = self.patterns['amount'].findall(text)
            amounts = [float(a.replace(',', '').replace(' ', '')) for a in amounts if a]
            # Filter out unreasonably large numbers (probably phone numbers etc)
            amounts = [a for a in amounts if a < 10000000]
            if amounts:
                invoice.grand_total = max(amounts)
    
    def _extract_bank_details(self, text: str, text_upper: str, invoice: InvoiceData):
        """Extract bank details."""
        
        # Bank name
        bank_match = re.search(r'(?:bank|branch)[\s:]*([A-Za-z\s]+(?:bank)?)', text, re.I)
        if bank_match:
            invoice.bank_name = bank_match.group(1).strip()
        
        # Account number (fuzzy match a/c, ac, account, etc.)
        for kw in ['a/c', 'ac', 'account', 'acct', 'acc']:
            pattern = rf'{kw}[\s.:no#]*[:\s#]+(\d{{9,18}})'
            match = re.search(pattern, text, re.I)
            if match:
                invoice.account_number = match.group(1)
                break
        
        # IFSC
        ifsc_match = self.patterns['ifsc'].search(text_upper)
        if ifsc_match:
            invoice.ifsc_code = ifsc_match.group()
    
    def to_dict(self, invoice: InvoiceData) -> Dict[str, Any]:
        """Convert invoice to dictionary."""
        data = asdict(invoice)
        return data
    
    def to_json(self, invoice: InvoiceData, indent: int = 2) -> str:
        """Convert invoice to JSON string."""
        return json.dumps(self.to_dict(invoice), indent=indent, ensure_ascii=False)
    
    def get_summary(self, invoice: InvoiceData) -> str:
        """Get human-readable summary."""
        lines = []
        lines.append("=" * 60)
        lines.append("📄 INVOICE SUMMARY")
        lines.append("=" * 60)
        
        if invoice.invoice_number:
            lines.append(f"Invoice #: {invoice.invoice_number}")
        if invoice.invoice_date:
            lines.append(f"Date: {invoice.invoice_date}")
        if invoice.due_date:
            lines.append(f"Due: {invoice.due_date}")
        if invoice.po_number:
            lines.append(f"PO #: {invoice.po_number}")
        
        lines.append("\n👤 SELLER:")
        if invoice.seller_name:
            lines.append(f"  {invoice.seller_name}")
        if invoice.seller_address:
            lines.append(f"  {invoice.seller_address}")
        if invoice.seller_phone:
            lines.append(f"  📞 {invoice.seller_phone}")
        if invoice.seller_gstin:
            lines.append(f"  GSTIN: {invoice.seller_gstin}")
        
        lines.append("\n👤 BUYER:")
        if invoice.buyer_name:
            lines.append(f"  {invoice.buyer_name}")
        if invoice.buyer_address:
            lines.append(f"  {invoice.buyer_address}")
        if invoice.buyer_phone:
            lines.append(f"  📞 {invoice.buyer_phone}")
        if invoice.buyer_gstin:
            lines.append(f"  GSTIN: {invoice.buyer_gstin}")
        
        if invoice.items:
            lines.append(f"\n📦 ITEMS ({len(invoice.items)}):")
            lines.append("-" * 50)
            for item in invoice.items:
                lines.append(f"  {item.sr_no}. {item.description}")
                if item.quantity and item.unit_price:
                    lines.append(f"     {item.quantity} {item.unit} × {item.unit_price:,.2f} = {item.amount:,.2f}")
                else:
                    lines.append(f"     Amount: {item.amount:,.2f}")
        
        lines.append("\n💰 AMOUNTS:")
        if invoice.subtotal:
            lines.append(f"  Subtotal: {invoice.subtotal:,.2f}")
        if invoice.discount:
            lines.append(f"  Discount: -{invoice.discount:,.2f}")
        if invoice.cgst:
            lines.append(f"  CGST: {invoice.cgst:,.2f}")
        if invoice.sgst:
            lines.append(f"  SGST: {invoice.sgst:,.2f}")
        if invoice.igst:
            lines.append(f"  IGST: {invoice.igst:,.2f}")
        if invoice.tax_total:
            lines.append(f"  Tax: {invoice.tax_total:,.2f}")
        if invoice.shipping:
            lines.append(f"  Shipping: {invoice.shipping:,.2f}")
        if invoice.grand_total:
            lines.append(f"  💵 TOTAL: {invoice.grand_total:,.2f}")
        if invoice.amount_paid:
            lines.append(f"  Paid: {invoice.amount_paid:,.2f}")
        if invoice.balance_due:
            lines.append(f"  Balance: {invoice.balance_due:,.2f}")
        
        if invoice.bank_name or invoice.account_number:
            lines.append("\n🏦 BANK:")
            if invoice.bank_name:
                lines.append(f"  {invoice.bank_name}")
            if invoice.account_number:
                lines.append(f"  A/C: {invoice.account_number}")
            if invoice.ifsc_code:
                lines.append(f"  IFSC: {invoice.ifsc_code}")
        
        lines.append("=" * 60)
        return "\n".join(lines)


def extract_invoice(image_path: str, ocr_processor=None) -> Dict[str, Any]:
    """
    Main function to extract invoice from image.
    
    Args:
        image_path: Path to invoice image
        ocr_processor: Optional pre-initialized OCRProcessor
        
    Returns:
        Dictionary with extracted data
    """
    from ocr_utils import OCRProcessor
    
    # Initialize
    if ocr_processor is None:
        ocr_processor = OCRProcessor(lang='en')
    
    extractor = FastInvoiceExtractor(fuzzy_threshold=65)
    
    # OCR
    ocr_text = ocr_processor.process_image(image_path)
    if not ocr_text:
        return {"error": "OCR failed", "raw_text": None}
    
    # Extract
    invoice = extractor.extract(ocr_text)
    
    return {
        "raw_text": ocr_text,
        "invoice": extractor.to_dict(invoice),
        "summary": extractor.get_summary(invoice)
    }


if __name__ == '__main__':
    import sys
    
    image_path = sys.argv[1] if len(sys.argv) > 1 else "../sample1.jpg"
    
    if not os.path.exists(image_path):
        print(f"❌ File not found: {image_path}")
        sys.exit(1)
    
    print(f"📄 Processing: {image_path}")
    print("-" * 60)
    
    result = extract_invoice(image_path)
    
    if "error" in result:
        print(f"❌ {result['error']}")
    else:
        print(result['summary'])
        print("\n📊 FULL JSON:")
        print("-" * 60)
        print(json.dumps(result['invoice'], indent=2, ensure_ascii=False))
