from google import genai
from google.genai import types
from dotenv import load_dotenv
import os
import hashlib
from pathlib import Path
from models import db, Invoice
import json
from datetime import date

def store_data(file_path, raw_text, response):
    try:
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            hasher.update(f.read())
        file_hash = hasher.hexdigest()

        parsed_response = json.loads(response)

        record = Invoice(
            source_file_name = Path(file_path).name,
            source_file_hash = file_hash,
            raw_text = raw_text,
            raw_extracted_json = parsed_response.get("raw_extracted_json"),

            vendor = parsed_response.get("vendor"),
            invoice = parsed_response.get("invoice"),
            items = parsed_response.get("items"),
            amounts = parsed_response.get("amounts"),
            classification = parsed_response.get("classification"),
            rule_trace = parsed_response.get("rule_trace"),

            confidence_score = parsed_response.get("confidence_score"),
            doc_score = parsed_response.get("doc_score"),
        )

        db.session.add(record)
        db.session.commit()
        return record

    except Exception as e:
        db.session.rollback()
        print("DB INSERT ERROR:", e)
        raise

def ocr(file):
    load_dotenv()
    gemini_api_key = os.getenv('GOOGLE_API_KEY')
    gemini_client = genai.Client(api_key=gemini_api_key)

    filepath_str = f"{file['file_path']}"
    filepath = Path(filepath_str)

    prompt_text_extraction = """

    Extract all readable text from the provided document exactly as it appears.
    Preserve line breaks and ordering as much as possible.
    Do not summarize, analyze, or interpret.
    Return only the extracted text.

    """

    response1 = gemini_client.models.generate_content(
    model="gemini-3-flash-preview",
    contents=[
        types.Part.from_bytes(
            data=filepath.read_bytes(),
            mime_type='application/pdf',
        ),
        prompt_text_extraction],
    config=types.GenerateContentConfig(temperature=0.1, thinking_config=types.ThinkingConfig(thinking_level='low')),
    )
    OCR_TEXT = response1.text

    PROMPT_TEMPLATE = """

    Your task is to extract structured invoice data from OCR text and return a single well-formed nested JSON object that is immediately usable for database storage and downstream analytics.

    You MUST:
    1. Extract all available invoice fields.
    2. Normalize formats (dates → YYYY-MM-DD, numbers → float).
    3. Perform India-specific validation checks.
    4. Flag missing or inconsistent information.
    5. Never hallucinate values. Use null if unavailable.
    6. Always return valid JSON only (no markdown, no explanations).

    --------------------------------------------------
    OCR TEXT START

    {ocr_text}

    OCR TEXT END
    --------------------------------------------------

    --------------------------------------------------
    OUTPUT REQUIREMENTS
    --------------------------------------------------

    Return exactly ONE JSON object with the following schema:

    {{
    "raw_extracted_json": object,

    "vendor": {{
        "vendor_name": string | null,
        "vendor_gstin": string | null,
        "vendor_pan": string | null
    }},

    "invoice": {{
        "invoice_number": string | null,
        "invoice_date": string | null,
        "invoice_period": {{
        "start": string | null,
        "end": string | null
        }},
        "currency": string | null,
        "payment_due_date": string | null,
        "payment_terms_days": number | null
    }},

    "items": [
        {{
        "description": string | null,
        "hsn_sac": string | null,
        "quantity": number | null,
        "unit_price": number | null,
        "tax_rate": number | null,
        "taxable_value": number | null,
        "cgst": number | null,
        "sgst": number | null,
        "igst": number | null,
        "total_value": number | null
        }}
    ],

    "amounts": {{
        "taxable_amount": number | null,
        "cgst_amount": number | null,
        "sgst_amount": number | null,
        "igst_amount": number | null,
        "total_tax_amount": number | null,
        "invoice_total_amount": number | null,
        "tax_applicable": boolean
    }},

    "classification": {{
        "expense_type": "OpEx" | "CapEx" | null,
        "ledger_category": "Assets" | "Liabilities" | "Equity" | "Revenue" | "Expenses" | null
    }},

    "rule_trace": [
        {{
        "rule_name": string,
        "status": "PASS" | "WARNING" | "FAIL" | "NOT_APPLICABLE",
        "message": string
        }}
    ],

    "confidence_score": number - 0 to 100
    "doc_score": "ACCEPTABLE" | "WARNING" | "CRITICAL"
    }}

    --------------------------------------------------
    EXTRACTION RULES
    --------------------------------------------------

    • Store all intermediate extracted fields in "raw_extracted_json".
    • If a field is missing or unreadable → use null.
    • Use only the headings given in the format.
    • Never invent values.

    --------------------------------------------------
    NORMALIZATION RULES
    --------------------------------------------------

    • Dates → YYYY-MM-DD
    • Amounts → float (no currency symbols, commas removed)
    • GSTIN → uppercase, no spaces
    • PAN → uppercase
    • Currency → ISO code if possible (INR, USD, etc.)

    --------------------------------------------------
    INDIA-SPECIFIC VALIDATION RULES (rule_trace)
    --------------------------------------------------

    Evaluate and log each rule independently:

    1. GST CALCULATION MATCH
    - Verify: taxable_amount + total_tax_amount ≈ invoice_total_amount
    - Verify CGST + SGST + IGST = total_tax_amount
    - Allow tolerance of ±1 INR for rounding.

    2. GST / PAN PRESENCE
    - If tax_applicable = true:
        - GSTIN must exist → else WARNING
        - PAN must exist → else WARNING

    3. DATE VALIDITY
    - Use {date_today} as Current Date
    - Invoice date must not be in the future → FAIL
    - Invoice date older than 18 months → WARNING

    4. TAX STRUCTURE CONSISTENCY
    - If IGST > 0 → CGST and SGST must be 0
    - If CGST or SGST > 0 → IGST must be 0
    - Otherwise → FAIL

    5. PAYMENT TERMS CONSISTENCY
    - If payment_terms_days present → validate payment_due_date matches invoice_date + terms
    - Mismatch → WARNING

    --------------------------------------------------
    FLAGGING RULES
    --------------------------------------------------

    • If a required field is missing but expected → add WARNING in rule_trace.
    • If logically incorrect → FAIL.
    • If not applicable → NOT_APPLICABLE.

    --------------------------------------------------
    DOCUMENT SCORING
    --------------------------------------------------

    Determine final doc_score:

    • ACCEPTABLE
    - No FAIL
    - LESS THAN OR EQUAL TO 2 WARNINGS

    • WARNING
    - No FAIL
    - GREATER THAN 2 WARNINGS

    • CRITICAL
    - Any FAIL exists

    --------------------------------------------------
    CONFIDENCE SCORE
    --------------------------------------------------

    Compute confidence_score (0-100) based on:
    • Field completeness
    • Numeric consistency
    • OCR clarity
    • Rule success rate

    Higher completeness + fewer warnings = higher score.

    --------------------------------------------------
    OUTPUT STRICTNESS
    --------------------------------------------------

    Return ONLY valid JSON.
    No commentary.
    No markdown.
    No explanations.
    No trailing commas.

    """

    prompt_for_invoice = PROMPT_TEMPLATE.format(
        ocr_text=OCR_TEXT, date_today=date.today().isoformat(),
    )

    response_invoice = gemini_client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=[prompt_for_invoice],
        config=types.GenerateContentConfig(
            system_instruction="You are a senior Chartered Accountant and Data Validation Agent specializing in Indian GST and Invoice compliance.",
            temperature=0.2, thinking_config=types.ThinkingConfig(thinking_level='medium')
        )
    )
    # print(response_invoice.text)
    store_data(filepath_str, OCR_TEXT, response_invoice.text)