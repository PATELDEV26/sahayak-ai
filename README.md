# SahayakAI — Setup Guide

## Tesseract OCR — Language Pack Installation

SahayakAI supports **Gujarati**, **Hindi**, and **English** document OCR.

### Step 1 — Install Language Packs

After installing Tesseract OCR, you need to add the Indian language data files.

#### Option A — During Tesseract Installation
Run the Tesseract installer again and select the extra language packs (Gujarati `guj`, Hindi `hin`).

#### Option B — Manual Download
1. Go to: https://github.com/tesseract-ocr/tessdata
2. Download these `.traineddata` files:
   - `guj.traineddata` — Gujarati
   - `hin.traineddata` — Hindi
   - `eng.traineddata` — English *(usually already present)*
3. Copy them to:
   ```
   C:\Program Files\Tesseract-OCR\tessdata\
   ```
4. Restart the Flask app.

> **Tip:** If Tesseract throws a "language not found" error, it means the `.traineddata` file is missing from the `tessdata/` folder. Re-download it from the link above.

---

## Python Dependencies

### Step 2 — Install Required Libraries

```bash
pip install -r requirements.txt
```

Or manually:

```bash
pip install flask pandas reportlab werkzeug python-dotenv \
            pytesseract Pillow opencv-python numpy \
            "googletrans==4.0.0rc1" langdetect
```

> **Important:** Use `googletrans==4.0.0rc1` exactly — version 3.x is broken and version 4.0.0 stable does not exist. Do **not** change the version.

---

## Running the App

```bash
python app.py
```

The server starts at: http://127.0.0.1:5000

---

## Multilingual OCR — How It Works

| Feature | Detail |
|---|---|
| **Languages supported** | English, Gujarati, Hindi |
| **Auto-detection** | Uses Unicode block analysis to identify dominant script |
| **Digit normalization** | Gujarati ૧૨૩ → 123, Devanagari १२३ → 123 |
| **Name translation** | Names in Gujarati/Hindi script are translated to English via `googletrans` |
| **Fallback** | If translation fails (network issue), original OCR text is returned |
| **Form fill** | All form fields are always filled in English regardless of source language |
| **UI badge** | A coloured badge shows which language was detected and that it was translated |

---

## Tessdata Verification

To verify your installed languages:

```bash
tesseract --list-langs
```

Expected output should include: `eng`, `hin`, `guj`
