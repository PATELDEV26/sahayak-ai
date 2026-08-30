import os
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, session, send_file, jsonify
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

load_dotenv()
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from datetime import datetime
import io
import re
import pytesseract
from PIL import Image
import cv2
import numpy as np
import google.generativeai as genai
try:
    from googletrans import Translator
    _translator = Translator()
except Exception:
    _translator = None

# ── Gujarati digit mapping ──────────────────────────────────────────────────
GUJARATI_DIGITS = {
    '\u0AE6': '0', '\u0AE7': '1', '\u0AE8': '2', '\u0AE9': '3', '\u0AEA': '4',
    '\u0AEB': '5', '\u0AEC': '6', '\u0AED': '7', '\u0AEE': '8', '\u0AEF': '9'
}

# ── Hindi / Devanagari digit mapping ───────────────────────────────────────
HINDI_DIGITS = {
    '\u0966': '0', '\u0967': '1', '\u0968': '2', '\u0969': '3', '\u096A': '4',
    '\u096B': '5', '\u096C': '6', '\u096D': '7', '\u096E': '8', '\u096F': '9'
}


def normalize_digits(text):
    """Replace Gujarati and Devanagari digits with ASCII digits."""
    for k, v in GUJARATI_DIGITS.items():
        text = text.replace(k, v)
    for k, v in HINDI_DIGITS.items():
        text = text.replace(k, v)
    return text


def detect_doc_language(text):
    """Detect whether document is primarily Gujarati, Hindi, or English."""
    gujarati_chars = len(re.findall(r'[\u0A80-\u0AFF]', text))
    hindi_chars    = len(re.findall(r'[\u0900-\u097F]', text))
    english_chars  = len(re.findall(r'[A-Za-z]', text))
    total = gujarati_chars + hindi_chars + english_chars
    if total == 0:
        return 'eng'
    if gujarati_chars > hindi_chars and gujarati_chars > english_chars:
        return 'guj'
    if hindi_chars > gujarati_chars and hindi_chars > english_chars:
        return 'hin'
    return 'eng'


def to_english(text, source_lang):
    """Translate text to English using googletrans; fall back to original on failure."""
    if not text or not text.strip():
        return text
    if source_lang == 'eng':
        return text
    if _translator is None:
        return text
    try:
        lang_map = {'guj': 'gu', 'hin': 'hi'}
        src = lang_map.get(source_lang, 'auto')
        result = _translator.translate(text.strip(), src=src, dest='en')
        return result.text.strip().title()
    except Exception:
        try:
            result = _translator.translate(text.strip(), dest='en')
            return result.text.strip().title()
        except Exception:
            return text


INDIAN_STATES = [
    "Andhra Pradesh","Arunachal Pradesh","Assam","Bihar","Chhattisgarh",
    "Goa","Gujarat","Haryana","Himachal Pradesh","Jharkhand","Karnataka",
    "Kerala","Madhya Pradesh","Maharashtra","Manipur","Meghalaya","Mizoram",
    "Nagaland","Odisha","Punjab","Rajasthan","Sikkim","Tamil Nadu","Telangana",
    "Tripura","Uttar Pradesh","Uttarakhand","West Bengal","Delhi","Jammu",
    "Jammu and Kashmir","Ladakh","Puducherry"
]

# If tesseract is not in PATH, set manually:
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


def preprocess_image(image_bytes):
    """Apply robust OpenCV preprocessing (CLAHE, deskewing, edge-preserving denoising) optimized for Tesseract LSTM."""
    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Could not decode image")

        # Upscale small images for better OCR resolution
        h, w = img.shape[:2]
        if w < 1600:
            scale = 1600 / w
            img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

        # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization) in LAB space
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
        cl = clahe.apply(l)
        limg = cv2.merge((cl, a, b))
        img = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)

        # Deskewing
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        coords = np.column_stack(np.where(gray < 200))
        if len(coords) > 100:
            angle = cv2.minAreaRect(coords)[-1]
            if angle < -45:
                angle = -(90 + angle)
            else:
                angle = -angle
            if abs(angle) < 30 and abs(angle) > 0.5:
                (h2, w2) = img.shape[:2]
                center = (w2 // 2, h2 // 2)
                M = cv2.getRotationMatrix2D(center, angle, 1.0)
                gray = cv2.warpAffine(gray, M, (w2, h2),
                    flags=cv2.INTER_CUBIC,
                    borderMode=cv2.BORDER_REPLICATE,
                    borderValue=255)

        # Edge-preserving denoising (Bilateral filter preserves letter strokes)
        clean_gray = cv2.bilateralFilter(gray, 7, 50, 50)
        return Image.fromarray(clean_gray)
    except Exception:
        return Image.open(io.BytesIO(image_bytes))


def auto_orient_image(pil_img):
    """Automatically detect image rotation (0, 90, 180, 270 degrees) and rotate upright."""
    best_img = pil_img
    best_score = -1

    for angle in [0, 90, 180, 270]:
        rotated = pil_img.rotate(angle, expand=True) if angle != 0 else pil_img
        try:
            text = pytesseract.image_to_string(rotated, lang='eng+guj+hin')
        except Exception:
            try:
                text = pytesseract.image_to_string(rotated)
            except Exception:
                text = ""

        score = 0
        text_lower = text.lower()

        keywords = [
            'government', 'india', 'dob', 'birth', 'year', 'male', 'female',
            'aadhaar', 'unique', 'authority', 'sarkar', 'bharat', 'gujarat',
            'identification', 'father', 'name', 'address', 'card', 'issue',
            'મહિલા', 'પુરૂષ', 'જન્મ', 'સરકાર', 'ભારત', 'આધાર', 'તારીખ',
            'महिला', 'पुरुष', 'जन्म', 'सरकार', 'भारत', 'आधार', 'तिथि'
        ]
        for kw in keywords:
            if kw in text_lower or kw in text:
                score += 25

        score += len(re.findall(r'\b\d{4}\b', text)) * 8
        score += len(re.findall(r'\d{2}[\/\-\.]\d{2}[\/\-\.]\d{4}', text)) * 50
        score += len(re.findall(r'\b(19\d{2}|20\d{2})\b', text)) * 15

        if score > best_score:
            best_score = score
            best_img = rotated

    return best_img


def evaluate_ocr_confidence(pil_img, extracted_text):
    """Evaluate OCR confidence score and flag low-quality document scans."""
    try:
        data = pytesseract.image_to_data(pil_img, output_type=pytesseract.Output.DICT)
        conf_scores = [int(c) for c in data['conf'] if int(c) >= 0]
        score = sum(conf_scores) / max(len(conf_scores), 1)
    except Exception:
        words = [w for w in extracted_text.split() if len(w) >= 2]
        score = min(len(words) * 8.0, 85.0)

    words_count = len([w for w in extracted_text.split() if len(w) >= 2])
    low_conf = score < 40.0 or words_count < 3
    warning_msg = (
        "Warning: Low OCR confidence score. Document photo may be blurry, dark, or skewed. Please re-upload a clearer image."
        if low_conf else None
    )
    return round(score, 1), low_conf, warning_msg


def extract_text_lines(image_bytes, languages="eng"):
    pil_img = preprocess_image(image_bytes)
    pil_img = auto_orient_image(pil_img)
    raw_text = pytesseract.image_to_string(pil_img, lang=languages)
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    return raw_text, lines


# ── State name lookup tables ────────────────────────────────────────────────
INDIAN_STATES_GUJ = {
    '\u0A97\u0AC1\u0A9C\u0AB0\u0ABE\u0AA4': 'Gujarat',
    '\u0AAE\u0AB9\u0ABE\u0AB0\u0ABE\u0AB7\u0ACD\u0A9F\u0ACD\u0AB0': 'Maharashtra',
    '\u0AB0\u0ABE\u0A9C\u0AB8\u0ACD\u0AA5\u0ABE\u0AA8': 'Rajasthan',
    '\u0AAE\u0AA7\u0ACD\u0AAF \u0AAA\u0ACD\u0AB0\u0AA6\u0AC7\u0AB6': 'Madhya Pradesh',
    '\u0A89\u0AA4\u0ACD\u0AA4\u0AB0 \u0AAA\u0ACD\u0AB0\u0AA6\u0AC7\u0AB6': 'Uttar Pradesh',
    '\u0AA6\u0ABF\u0AB2\u0ACD\u0AB9\u0AC0': 'Delhi',
    '\u0A95\u0AB0\u0ACD\u0AA3\u0ABE\u0A9F\u0A95': 'Karnataka',
    '\u0AA4\u0AAE\u0ABF\u0AB2 \u0AA8\u0ABE\u0AA1\u0AC1': 'Tamil Nadu',
    '\u0AAA\u0AB6\u0ACD\u0A9A\u0ABF\u0AAE \u0AAC\u0A82\u0A97\u0ABE\u0AB3': 'West Bengal',
    '\u0AAC\u0ABF\u0AB9\u0ABE\u0AB0': 'Bihar',
    '\u0A93\u0AA1\u0ABF\u0AB6\u0ABE': 'Odisha',
    '\u0A95\u0AC7\u0AB0\u0AB3': 'Kerala',
    '\u0AAA\u0A82\u0A9C\u0ABE\u0AAC': 'Punjab',
    '\u0AB9\u0AB0\u0ABF\u0AAF\u0ABE\u0AA3\u0ABE': 'Haryana',
    '\u0A86\u0AB8\u0ABE\u0AAE': 'Assam',
    '\u0A9D\u0ABE\u0AB0\u0A96\u0A82\u0AA1': 'Jharkhand',
    '\u0A9B\u0AA4\u0ACD\u0AA4\u0AC0\u0AB8\u0A97\u0AA2': 'Chhattisgarh',
    '\u0A89\u0AA4\u0ACD\u0AA4\u0AB0\u0ABE\u0A96\u0A82\u0AA1': 'Uttarakhand',
    '\u0A97\u0ACB\u0A86': 'Goa',
    '\u0AA4\u0AC7\u0AB2\u0A82\u0A97\u0ABE\u0AA3\u0ABE': 'Telangana',
}

INDIAN_STATES_HIN = {
    '\u0917\u0941\u091C\u0930\u093E\u0924': 'Gujarat',
    '\u092E\u0939\u093E\u0930\u093E\u0937\u094D\u091F\u094D\u0930': 'Maharashtra',
    '\u0930\u093E\u091C\u0938\u094D\u0925\u093E\u0928': 'Rajasthan',
    '\u092E\u0927\u094D\u092F \u092A\u094D\u0930\u0926\u0947\u0936': 'Madhya Pradesh',
    '\u0909\u0924\u094D\u0924\u0930 \u092A\u094D\u0930\u0926\u0947\u0936': 'Uttar Pradesh',
    '\u0926\u093F\u0932\u094D\u0932\u0940': 'Delhi',
    '\u0915\u0930\u094D\u0928\u093E\u091F\u0915': 'Karnataka',
    '\u0924\u092E\u093F\u0932 \u0928\u093E\u0921\u0941': 'Tamil Nadu',
    '\u092A\u0936\u094D\u091A\u093F\u092E \u092C\u0902\u0917\u093E\u0932': 'West Bengal',
    '\u092C\u093F\u0939\u093E\u0930': 'Bihar',
    '\u0913\u0921\u093F\u0936\u093E': 'Odisha',
    '\u0915\u0947\u0930\u0932': 'Kerala',
    '\u092A\u0902\u091C\u093E\u092C': 'Punjab',
    '\u0939\u0930\u093F\u092F\u093E\u0923\u093E': 'Haryana',
    '\u0905\u0938\u092E': 'Assam',
    '\u091D\u093E\u0930\u0916\u0902\u0921': 'Jharkhand',
    '\u091B\u0924\u094D\u0924\u0940\u0938\u0917\u0922': 'Chhattisgarh',
    '\u0909\u0924\u094D\u0924\u0930\u093E\u0916\u0902\u0921': 'Uttarakhand',
    '\u0917\u094B\u0935\u093E': 'Goa',
    '\u0924\u0947\u0932\u0902\u0917\u093E\u0923\u093E': 'Telangana',
}


def extract_aadhaar_data(image_bytes):
    """Extract Aadhaar card data with Gujarati, Hindi, and English support."""
    pil_img = preprocess_image(image_bytes)
    pil_img = auto_orient_image(pil_img)

    result = {
        "full_name": "",
        "date_of_birth": "",
        "gender": "",
        "aadhaar_last4": "",
        "address_state": "",
        "detected_language": "eng",
        "confidence": "medium"
    }

    # ── Multi-pass OCR in each language ───────────────────────────────────
    texts = {}
    for lang, cfg in [
        ('eng', r'--oem 3 --psm 4 -l eng'),
        ('guj', r'--oem 3 --psm 4 -l guj'),
        ('hin', r'--oem 3 --psm 4 -l hin'),
    ]:
        try:
            texts[lang] = pytesseract.image_to_string(pil_img, config=cfg)
        except Exception:
            texts[lang] = ""

    # Combined pass for mixed documents
    try:
        combined_text = pytesseract.image_to_string(
            pil_img, config=r'--oem 3 --psm 4 -l eng+guj+hin')
    except Exception:
        combined_text = texts.get('eng', '')

    # Normalize digits in all passes
    for lang in texts:
        texts[lang] = normalize_digits(texts[lang])
    combined_text = normalize_digits(combined_text)

    # Detect dominant script
    doc_lang = detect_doc_language(combined_text)
    result["detected_language"] = doc_lang

    primary_text = texts.get(doc_lang, combined_text) or combined_text
    all_text = combined_text  # use combined for number/date extraction

    lines     = [l.strip() for l in primary_text.splitlines() if l.strip()]
    all_lines = [l.strip() for l in all_text.splitlines() if l.strip()]

    # ── DOB ───────────────────────────────────────────────────────────────
    dob_patterns = [
        r'\b(\d{2}[\/\-\.]\d{2}[\/\-\.]\d{4})\b',
        r'(?:DOB|Date of Birth|D\.O\.B|\u0A9C\u0AA8\u0ACD\u0AAE \u0AA4\u0ABE\u0AB0\u0AC0\u0A96|\u091C\u0928\u094D\u092E \u0924\u093F\u0925\u093F)[:\s]+(\d{2}[\/\-\.]\d{2}[\/\-\.]\d{4})',
        r'(?:Year of Birth|YOB|\u0A9C\u0AA8\u0ACD\u0AAE \u0AB5\u0AB0\u0ACD\u0AB7|\u091C\u0928\u094D\u092E \u0935\u0930\u094D\u0937)[:\s]+(\d{4})',
    ]
    for pat in dob_patterns:
        m = re.search(pat, all_text, re.IGNORECASE)
        if m and not result["date_of_birth"]:
            val = m.group(1).replace('-', '/').replace('.', '/')
            if len(val) == 4:
                val = f"01/01/{val}"
            result["date_of_birth"] = val
            break

    # ── Gender ────────────────────────────────────────────────────────────
    gender_patterns = {
        "Female": [
            r'\bFemale\b', r'\b\u092E\u0939\u093F\u0932\u093E\b', r'\b\u0938\u094D\u0924\u094D\u0930\u0940\b',
            r'\b\u0AB8\u0ACD\u0AA4\u0ACD\u0AB0\u0AC0\b', r'\b\u0AAE\u0AB9\u0ABF\u0AB2\u0ABE\b',
        ],
        "Male": [
            r'\bMale\b', r'\b\u092A\u0941\u0930\u0941\u0937\b',
            r'\b\u0AAA\u0AC1\u0AB0\u0AC1\u0AB7\b',
        ]
    }
    for gender, patterns in gender_patterns.items():
        for pat in patterns:
            if re.search(pat, all_text, re.IGNORECASE):
                result["gender"] = gender
                break
        if result["gender"]:
            break

    # ── Aadhaar number ────────────────────────────────────────────────────
    aadhaar_match = re.search(r'\b\d{4}\s?\d{4}\s?(\d{4})\b', all_text)
    if aadhaar_match:
        result["aadhaar_last4"] = aadhaar_match.group(1)

    # ── State ─────────────────────────────────────────────────────────────
    for state in INDIAN_STATES:
        if re.search(rf'\b{re.escape(state)}\b', all_text, re.IGNORECASE):
            result["address_state"] = state
            break
    if not result["address_state"]:
        for guj_name, eng_name in INDIAN_STATES_GUJ.items():
            if guj_name in all_text:
                result["address_state"] = eng_name
                break
    if not result["address_state"]:
        for hin_name, eng_name in INDIAN_STATES_HIN.items():
            if hin_name in all_text:
                result["address_state"] = eng_name
                break
    if not result["address_state"] and doc_lang == 'guj':
        result["address_state"] = "Gujarat"

    # ── Name ──────────────────────────────────────────────────────────────
    skip_keywords = [
        'government', 'india', 'aadhaar', 'aadhar', 'dob', 'male', 'female',
        'year', 'address', 'uid', 'unique', 'authority', 'department',
        'income', 'certificate', 'issued', 'district', 'taluka', 'village',
        'republic', 'enrollment', 'enrolment', 'uidai',
        '\u092D\u093E\u0930\u0924', '\u0938\u0930\u0915\u093E\u0930',   # Hindi: bharat, sarkar
        '\u0AAD\u0ABE\u0AB0\u0AA4', '\u0AB8\u0AB0\u0A95\u0ABE\u0AB0',   # Gujarati: bharat, sarkar
        '\u0A86\u0AA7\u0ABE\u0AB0',                                       # Gujarati: aadhaar
    ]

    # 1. DOB-Anchored Name Extraction (High Precision for Aadhaar cards)
    dob_line_idx = -1
    for idx, l in enumerate(all_lines):
        if re.search(r'\d{2}[\/\-\.]\d{2}[\/\-\.]\d{4}', l) or 'dob' in l.lower() or 'birth' in l.lower() or 'જન્મ' in l or 'जन्म' in l:
            dob_line_idx = idx
            break

    if dob_line_idx > 0:
        for offset in [1, 2]:
            if dob_line_idx - offset >= 0:
                cand = all_lines[dob_line_idx - offset].strip()
                cand_clean = re.sub(r'[^A-Za-z\u0900-\u097F\u0A80-\u0AFF\s\.]', '', cand).strip()
                if (len(cand_clean) >= 3
                        and len(cand_clean.split()) <= 6
                        and not any(kw in cand_clean.lower() for kw in skip_keywords)
                        and not any(kw in cand_clean for kw in ['ભારત', 'સરકાર', 'भारत', 'सरकार'])):
                    if re.search(r'[\u0A80-\u0AFF\u0900-\u097F]', cand_clean):
                        translated = to_english(cand_clean, doc_lang)
                        if translated and re.match(r'^[A-Za-z\s\.]+$', translated) and len(translated) >= 3:
                            result["full_name"] = translated
                            break
                    elif re.match(r'^[A-Za-z\s\.]+$', cand_clean):
                        result["full_name"] = cand_clean.title()
                        break

    # 2. General scan if DOB-anchored extraction did not find full_name
    if not result["full_name"]:
        if doc_lang == 'eng':
            for line in lines:
                clean = line.strip()
                if (len(clean) >= 4
                        and len(clean.split()) <= 5
                        and not re.search(r'\d', clean)
                        and re.match(r'^[A-Za-z\s\.]+$', clean)
                        and not any(kw in clean.lower() for kw in skip_keywords)):
                    result["full_name"] = clean.title()
                    break
        else:
            script_range = r'[\u0A80-\u0AFF]' if doc_lang == 'guj' else r'[\u0900-\u097F]'
            translated_skip = [
                'government', 'india', 'unique', 'authority', 'aadhaar',
                'address', 'district', 'state', 'certificate', 'income',
                'republic', 'department', 'village', 'taluka', 'resident'
            ]
            for candidate in lines[:20]:
                clean = candidate.strip()
                script_chars = len(re.findall(script_range, clean))
                total_chars  = len(clean.replace(' ', ''))
                if (total_chars > 0
                        and script_chars / total_chars > 0.5
                        and not re.search(r'\d', clean)
                        and 3 <= len(clean) <= 50
                        and len(clean.split()) <= 6
                        and not any(kw in clean for kw in skip_keywords)):
                    translated = to_english(clean, doc_lang)
                    if translated and not any(kw in translated.lower() for kw in translated_skip):
                        if re.match(r'^[A-Za-z\s\.]+$', translated):
                            result["full_name"] = translated
                            break
            if not result["full_name"]:
                for line in [l.strip() for l in combined_text.splitlines() if l.strip()]:
                    if (len(line) >= 4
                            and len(line.split()) <= 5
                            and not re.search(r'\d', line)
                            and re.match(r'^[A-Za-z\s\.]+$', line)
                            and not any(kw in line.lower() for kw in skip_keywords)):
                        result["full_name"] = line.title()
                        break

    # ── Confidence ────────────────────────────────────────────────────────
    filled = sum(1 for k, v in result.items()
                 if k not in ('confidence', 'detected_language') and v)
    result["confidence"] = "high" if filled >= 4 else "medium" if filled >= 2 else "low"

    return result


def extract_income_certificate_data(image_bytes):
    raw_text, lines = extract_text_lines(image_bytes)

    result = {
        "income": "",
        "full_name": "",
        "address_state": "",
        "confidence": "low"
    }

    amounts = []
    for match in re.finditer(r'(?:rs\.?|inr|₹)\s*([\d,]+(?:\.\d+)?)', raw_text, re.IGNORECASE):
        try:
            amounts.append(float(match.group(1).replace(',', '')))
        except ValueError:
            continue
    # Fallback: pick large standalone numbers (>=4 digits) if currency symbol missing
    for match in re.finditer(r'\b([\d,]{4,})\b', raw_text):
        try:
            amounts.append(float(match.group(1).replace(',', '')))
        except ValueError:
            continue

    if amounts:
        result["income"] = round(max(amounts), 2)

    # State and name detection similar to Aadhaar
    for line in lines:
        for state in INDIAN_STATES:
            if state.lower() in line.lower() and not result["address_state"]:
                result["address_state"] = state
                break

    skip_keywords = ['income', 'certificate', 'government', 'department', 'office', 'state']
    for line in lines:
        if (len(line) > 4
            and not any(kw in line.lower() for kw in skip_keywords)
            and not re.search(r'\d', line)
            and re.match(r'^[A-Za-z\s]+$', line)):
            result["full_name"] = line.strip().title()
            break

    filled = sum(1 for v in result.values() if v and v != "low")
    if filled >= 2:
        result["confidence"] = "medium"
    if filled >= 3:
        result["confidence"] = "high"

    return result


def _to_acres(value, unit):
    unit = unit.lower()
    if unit in ["acre", "acres"]:
        return value
    if unit in ["hectare", "hectares", "ha"]:
        return value * 2.47105
    if unit in ["guntha", "gunta", "gunthas", "guntas"]:
        return value * 0.0247105
    if unit in ["bigha", "bighas"]:
        return value * 0.619
    return value


def extract_land_document_data(image_bytes):
    raw_text, lines = extract_text_lines(image_bytes)

    result = {
        "land_owned": "",
        "address_state": "",
        "confidence": "low"
    }

    land_amount = None
    for match in re.finditer(r'([\d.,]+)\s*(acre|acres|hectare|hectares|ha|guntha|gunta|bigha|bighas)', raw_text, re.IGNORECASE):
        try:
            numeric_val = float(match.group(1).replace(',', ''))
            acres = _to_acres(numeric_val, match.group(2))
            land_amount = max(land_amount or 0, acres)
        except ValueError:
            continue

    if land_amount:
        result["land_owned"] = round(land_amount, 2)

    for line in lines:
        for state in INDIAN_STATES:
            if state.lower() in line.lower() and not result["address_state"]:
                result["address_state"] = state
                break

    if result["land_owned"] and result["address_state"]:
        result["confidence"] = "high"
    elif result["land_owned"]:
        result["confidence"] = "medium"

    return result


def extract_death_certificate_data(image_bytes):
    raw_text, lines = extract_text_lines(image_bytes)

    result = {
        "full_name": "",
        "gender": "",
        "death_date": "",
        "address_state": "",
        "confidence": "low"
    }

    date_match = re.search(r'(?:Date of Death|DOD|Death Date)[:\s]+(\d{2}[\/\-]\d{2}[\/\-]\d{4})', raw_text, re.IGNORECASE)
    if date_match:
        result["death_date"] = date_match.group(1).replace('-', '/')

    if re.search(r'\bFemale\b', raw_text, re.IGNORECASE):
        result["gender"] = "Female"
    elif re.search(r'\bMale\b', raw_text, re.IGNORECASE):
        result["gender"] = "Male"

    for line in lines:
        for state in INDIAN_STATES:
            if state.lower() in line.lower() and not result["address_state"]:
                result["address_state"] = state
                break

    skip_keywords = ['death', 'certificate', 'name of', 'hospital', 'municipal', 'registration']
    for line in lines:
        if (len(line) > 4
            and not any(kw in line.lower() for kw in skip_keywords)
            and not re.search(r'\d', line)
            and re.match(r'^[A-Za-z\s]+$', line)):
            result["full_name"] = line.strip().title()
            break

    filled = sum(1 for v in result.values() if v and v != "low")
    if filled >= 2:
        result["confidence"] = "medium"
    if filled >= 3:
        result["confidence"] = "high"

    return result


def extract_bpl_card_data(image_bytes):
    raw_text, lines = extract_text_lines(image_bytes)

    result = {
        "bpl": "",
        "address_state": "",
        "confidence": "low"
    }

    if re.search(r'\bbpl\b|below poverty line', raw_text, re.IGNORECASE):
        result["bpl"] = "Yes"

    for line in lines:
        for state in INDIAN_STATES:
            if state.lower() in line.lower() and not result["address_state"]:
                result["address_state"] = state
                break

    if result["bpl"]:
        result["confidence"] = "medium" if result["address_state"] else "low"

    return result

app = Flask(__name__)
app.secret_key = 'sahayak_ai_super_secret_key'

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB max size

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Helper function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Load schemes data
def load_schemes():
    try:
        csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'schemes.csv')
        df = pd.read_csv(csv_path)
        # Fill NaN values to avoid errors during comparison
        df['min_age'] = df['min_age'].fillna(0)
        df['max_age'] = df['max_age'].fillna(100)
        if 'income_ceiling' in df.columns:
            df['income_ceiling'] = df['income_ceiling'].fillna(99999999)
        elif 'max_income' in df.columns:
            df['max_income'] = df['max_income'].fillna(99999999)
        df['min_land'] = df['min_land'].fillna(0)
        return df
    except Exception as e:
        print(f"Error loading schemes: {e}")
        return pd.DataFrame()

@app.route('/')
def index():
    # Helper for last search session
    last_search = session.get('last_search', None)
    return render_template('index.html', last_search=last_search)

@app.route('/student')
def student_form():
    return render_template('student.html')

@app.route('/farmer')
def farmer_form():
    return render_template('farmer.html')

@app.route('/girls')
def girls_form():
    return render_template('girls.html')

@app.route('/others')
def others_form():
    return render_template('others.html')

def save_uploaded_files(files):
    saved_files_count = 0
    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            saved_files_count += 1
    return saved_files_count

def evaluate_schemes_for_profile(df, profile):
    """Core scheme eligibility matching engine handling overlapping state, caste, income, and category rules."""
    persona = str(profile.get('category', '')).strip().title()
    age = int(profile.get('age', 0))
    income = float(profile.get('income', 0))
    state = str(profile.get('state', 'All')).strip()
    caste_or_category = str(profile.get('caste', str(profile.get('category_caste', 'General')))).strip()
    disability = str(profile.get('disability', 'No')).strip()
    bpl = str(profile.get('bpl', 'No')).strip()
    land_owned = float(profile.get('land_owned', 0))
    sub_category = str(profile.get('sub_category', 'All')).strip()
    gender = str(profile.get('gender', 'All')).strip()

    if 'persona' in df.columns:
        persona_df = df[df['persona'].str.title() == persona]
    else:
        persona_df = df[df['category'].str.title() == persona]

    if persona == 'Others' and sub_category != 'All' and 'sub_category' in persona_df.columns:
        sub_mask = (persona_df['sub_category'] == 'All') | (persona_df['sub_category'].str.lower() == sub_category.lower())
        persona_df = persona_df[sub_mask]

    state_mask = (persona_df['state'] == 'All') | (persona_df['state'].str.lower() == state.lower())
    age_mask = (persona_df['min_age'] <= age) & (persona_df['max_age'] >= age)
    
    if 'gender' in persona_df.columns and gender != 'All':
        gender_mask = (persona_df['gender'] == 'All') | (persona_df['gender'].str.lower() == gender.lower())
    else:
        gender_mask = pd.Series(True, index=persona_df.index)

    filtered_df = persona_df[state_mask & age_mask & gender_mask]
    matches = []

    for _, row in filtered_df.iterrows():
        limit = float(row.get('income_ceiling', row.get('max_income', 0)))
        if limit > 0 and income > limit:
            continue

        scheme_caste = str(row.get('category', row.get('caste', 'All'))).strip()
        allowed_castes = [c.strip().upper() for c in re.split(r'[/,]', scheme_caste)]
        if 'ALL' not in allowed_castes and 'GENERAL' not in allowed_castes and caste_or_category.upper() not in allowed_castes:
            continue

        if str(row.get('disability_required', 'No')).strip().lower() == 'yes' and disability.lower() != 'yes':
            continue

        if str(row.get('bpl_required', 'No')).strip().lower() == 'yes' and bpl.lower() != 'yes':
            continue

        min_land = float(row.get('min_land', 0))
        if min_land > 0 and land_owned < min_land:
            continue

        matches.append(row.to_dict())

    return matches


@app.route('/check/<category>', methods=['POST'])
def check_eligibility(category):
    if request.method == 'POST':
        form_data = request.form.to_dict()
        files = request.files.getlist('documents')
        
        # Save files
        saved_count = save_uploaded_files(files)
        
        # Determine eligibility using Pandas
        df = load_schemes()
        name = form_data.get('full_name', '')
        profile = dict(form_data)
        profile['category'] = category

        matches = evaluate_schemes_for_profile(df, profile)

        # Save result to session or pass to template
        # We will pass directly
        
        # Session history
        session['last_search'] = {
            'name': name,
            'category': category.capitalize(),
            'count': len(matches),
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M")
        }

        return render_template('result.html', 
                               schemes=matches, 
                               user_name=name, 
                               category=category.capitalize(),
                               saved_count=saved_count,
                               user_data=form_data)

    return redirect(url_for('index'))

@app.route('/download_report', methods=['POST'])
def download_report():
    user_name = request.form.get('user_name')
    category = request.form.get('category')
    # We need to reconstruct the schemes list or pass it. 
    # For simplicity, we'll ask the front-end to send the scheme names or ids.
    # OR better, since this is a simple app, we can just print a generic eligibility receipt.
    # Let's use the scheme names passed hidden in the form.
    scheme_names = request.form.getlist('scheme_name')
    
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    # Header
    p.setFont("Helvetica-Bold", 24)
    p.drawString(50, height - 50, "SahayakAI - Eligibility Report")
    
    p.setFont("Helvetica", 12)
    p.drawString(50, height - 80, f"Date: {datetime.now().strftime('%Y-%m-%d')}")
    p.drawString(50, height - 100, f"User Name: {user_name}")
    p.drawString(50, height - 120, f"Category: {category}")
    
    p.line(50, height - 140, width - 50, height - 140)
    
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, height - 170, "Eligible Schemes:")
    
    y = height - 200
    p.setFont("Helvetica", 12)
    for name in scheme_names:
        if y < 50:
            p.showPage()
            y = height - 50
        p.drawString(70, y, f"- {name}")
        y -= 25
        
    p.drawString(50, y - 20, "Please visit the official government portals to apply.")
    
    p.showPage()
    p.save()
    
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"SahayakAI_Report_{user_name}.pdf", mimetype='application/pdf')

@app.route('/extract-document', methods=['POST'])
def extract_document():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']
    doc_type = request.form.get('doc_type', 'aadhaar').lower()
    ext = file.filename.rsplit('.', 1)[-1].lower()

    if ext not in ['jpg', 'jpeg', 'png']:
        return jsonify({"error": "Invalid file type. Use JPG or PNG"}), 400

    image_bytes = file.read()

    try:
        if doc_type == 'income':
            result = extract_income_certificate_data(image_bytes)
        elif doc_type == 'land':
            result = extract_land_document_data(image_bytes)
        elif doc_type == 'death':
            result = extract_death_certificate_data(image_bytes)
        elif doc_type == 'bpl':
            result = extract_bpl_card_data(image_bytes)
        else:
            result = extract_aadhaar_data(image_bytes)

        result['doc_type'] = doc_type
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
def get_schemes_context():
    try:
        with open('schemes.csv', 'r', encoding='utf-8') as f:
            return f.read()
    except:
        return ""

SCHEMES_DATA = get_schemes_context()

SYSTEM_PROMPT = """You are SahayakAI, a helpful assistant for poor rural citizens of India.
Your job is to help them understand government welfare schemes, how to fill
application forms, what documents they need, and whether they are eligible.

STRICT RULES:
1. ALWAYS reply in simple Hindi (Devanagari script). Use very simple words.
   Short sentences. As if talking to a village person with low education.
2. Only answer questions about: government schemes, form filling, required
   documents, eligibility criteria, how to apply.
3. If asked anything outside this scope, say:
   "मैं केवल सरकारी योजनाओं के बारे में मदद कर सकता हूं।"
4. Be warm, patient, and encouraging.
5. If the user types in English letters but the question is in Hindi
   (Hinglish), understand it and still reply in Hindi Devanagari.
6. Keep answers short — maximum 4-5 sentences per reply.
7. Never decide eligibility yourself — only explain what schemes say."""

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    message = data.get('message', '')
    history = data.get('history', [])
    
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        return jsonify({"reply": "API Key is missing."}), 500
    genai.configure(api_key=api_key)
    
    model = genai.GenerativeModel('gemini-3.5-flash', system_instruction=SYSTEM_PROMPT)
    
    formatted_history = []
    for msg in history:
        role = "user" if msg['role'] == "user" else "model"
        formatted_history.append({"role": role, "parts": [msg['content']]})
        
    try:
        chat_session = model.start_chat(history=formatted_history)
        response = chat_session.send_message(message)
        return jsonify({"reply": response.text})
    except Exception as e:
        return jsonify({"reply": "क्षमा करें, अभी सेवा उपलब्ध नहीं है। कृपया थोड़ी देर बाद प्रयास करें।"}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)
