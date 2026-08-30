

## 👨‍💻 DEVANSHI: Frontend User Interface & File Handling

**Focus Area:** Web Architecture, HTML/CSS, Client-Side Form Mechanics, and Jinja2 Templating
**Files Responsible For:** `templates/index.html`, `templates/student.html`, `templates/farmer.html`, `templates/result.html`, `templates/widower.html`, and `static/css`.

**Detailed Technical Explanation of the Implementation:**

*   **Architecture & User Flow Architecture:** 
    *   The frontend acts as the user's gateway. It uses standard HTML5 semantic tags for structure, heavily utilizing the `enctype="multipart/form-data"` attribute within the `<form>` tags. This specific encoding is strictly necessary, without it, image files (Aadhaar, Income Certificates) cannot be transmitted across HTTP POST requests to the Python server.
*   **Form Handling & Data Capture:** 
    *   To capture complex logic, you use dynamic `<select>` dropdowns and `<input>` forms. You capture constraints like `age` (number), `income` (floating points), `state` (dropdown lookup), and highly specific markers like a student's `caste` or a farmer's `land_amount`.
    *   For the file upload pipeline, the syntax `<input type="file" name="documents" multiple>` is used. The `multiple` keyword is critical as it instructs the browser to bundle a list of File objects into the payload, allowing concurrent processing of diverse documents.
*   **Dynamic Data Rendering (Jinja2):** 
    *   Instead of writing hardcoded HTML, Flask uses Jinja2 (`{% %}` syntax). In `result.html`, you receive backend data as a Python list of dictionaries. By using syntax like `{% for scheme in schemes %}`, you dynamically render UI cards for *only* the government schemes a user qualifies for. This completely decouples frontend logic from the backend.


## ⚙️ OM: Core Backend Engine & Scheme Evaluator

**Focus Area:** Flask Framework, HTTP Routing, and Pandas Data Engineering
**Files/Code Responsible For:** `app.py` (App configuration, Routing: `@app.route('/check')`, File saving routines, and Scheme matching script: `load_schemes`), and `schemes.csv`.

**Detailed Technical Explanation of the Implementation:**

*   **The Flask Server Core:** 
    *   Flask is utilized as a WSGI application. It listens on port 5000 and maps HTTP endpoints using `@app.route()`. Data from Devanshi’s frontend arrives here. You use `request.form.to_dict()` to instantly convert the entire HTTP POST form payload into a manageable Python Dictionary. 
    *   File payloads are pulled via `request.files.getlist('documents')`. For security, you wrap `secure_filename()` around incoming files to strip malicious path injections before saving them locally utilizing `os.path.join()`.
*   **Pandas Data Engineering & Cleaning:** 
    *   When evaluating eligibility, you immediately trigger `pd.read_csv('schemes.csv')`. Raw dataset rows are dangerous (they might have null values). To fix this, you implemented `.fillna()` algorithms. For instance, `df['max_income'] = df['max_income'].fillna(99999999)` guarantees that a scheme with no income ceiling doesn't accidentally crash the comparison logic.
*   **The Eligibility Algorithm (Boolean Masking):** 
    *   Instead of slow loops, you leverage Pandas Vectorization. You build "Masks" — `age_mask = (category_df['min_age'] <= age) & (category_df['max_age'] >= age)`. This mathematically applies binary arrays against the entire dataset in milliseconds.
    *   Next, `iterrows()` runs a line-by-line validation for category-specific edge cases (verifying if a farmer actually owns the `min_land` requested by a scheme or validating a widow's `BPL` flag).


## 🤖 DEV (Leader): Computer Vision & Regional Language OCR Engine

**Focus Area:** Image Pre-processing (OpenCV), Multilingual Tesseract OCR, PyTesseract, and Natural Language Processing (Translation)
**Files/Code Responsible For:** `app.py` Functions: `preprocess_image()`, `extract_text_lines()`, `detect_doc_language()`, `to_english()`.

**Detailed Technical Explanation of the Implementation:**

*   **OpenCV Image Preprocessing Pipeline (The "CV2" Stack):**
    *   Raw smartphone photos produce terrible OCR results. To fix this, you immediately decode incoming byte arrays into Numpy Matricies via `cv2.imdecode`.
    *   **Deskewing Algorithm:** If a document is rotated, you create a grayscale array, find pixels lower than a critical threshold (`< 200`), and calculate a bounding box (`cv2.minAreaRect`). By calculating the matrix angle, you apply an Affine Transform rotation (`cv2.warpAffine`) to forcibly straighten the document.
    *   **Enhancement Filters:** You chain `cv2.fastNlMeansDenoising` (to erase camera grain), and finally `cv2.adaptiveThreshold` using a Gaussian constant. This converts a blurry, grey image into a crystal-clear binary Black & White image, maximizing Tesseract's accuracy.
*   **Multilingual PyTesseract OCR:** 
    *   You bypassed native tesseract behaviors by explicitly injecting flags via python: `--oem 3 --psm 4 -l eng+guj+hin`. This commands the LSTM neural net inside Tesseract to parse English, Gujarati, and Hindi characters simultaneously block-by-block.
*   **Script Detection & Normalization via Unicode:** 
    *   How does the AI know it's reading Gujarati? You built `detect_doc_language()` using Regex Unicode Blocks `[\u0A80-\u0AFF]`. If the text contains more characters from this hexadecimal block than others, the system flags the document natively as Gujarati.
    *   You integrated the `googletrans` API to catch regional names dynamically and translate them into standard English. Finally, regional digits (like Gujarati ૧૨૩ or Hindi १२३) are surgically replaced using a Dictionary Map `normalize_digits()` to ensure that numbers are mathematically digestible later.


## 📄 ARYAN: Data Extraction Engine & Report Generation

**Focus Area:** Regex Parsing, Custom Logic Handlers, and ReportLab PDF Engine
**Files/Code Responsible For:** `app.py` Document Parsers (`extract_aadhaar_data`, `extract_income_certificate`, `extract_land_document_data`), and `download_report()`.

**Detailed Technical Explanation of the Implementation:**

*   **Advanced Regex Parsing:** 
    *   Tesseract outputs raw, unformatted text strings. You implemented advanced Regex (`re.search` / `re.finditer`) to extract needles from the haystack.
    *   For Aadhaar cards, you used `\b\d{4}\s?\d{4}\s?(\d{4})\b` to skip the first 8 digits (for privacy) and capture strictly the last 4 digits using group captures.
    *   For Birthdates, you mapped an array of potential identifiers: `(?:DOB|Date of Birth|\u0A9C\u0AA8\u0ACD\u0AAE \u0AA4\u0ABE\u0AB0\u0AC0\u0A96)[:\s]+(\d{2}[\/\-\.]\d{2})`. This catches dates whether they are formatted with slashes, dots, or dashes, and whether the prefix is in English or Gujarati.
*   **Intelligent Entity Resolution:**
    *   You created `_to_acres()`. When parsing land documents, OCR might find "Hectares", "Guntas", or "Bighas". You wrote logic to intercept these diverse units and automatically apply fixed mathematical conversions to standardize everything into "Acres" for the Pandas matching engine.
*   **Multilingual State Dictionary:** 
    *   If a document says "ગુજરાત", a standard English string match fails. You created hash-map dictionaries (`INDIAN_STATES_GUJ`) to strictly catch regional spellings and map them immediately back to the English "Gujarat".
*   **Dynamic Report Generation (ReportLab PDF):** 
    *   Instead of just showing HTML, you allow users to take the data with them. Using `reportlab.pdfgen.canvas`, you create an in-memory byte buffer (`io.BytesIO`). You programmatically draw lines, iterate dynamically over the winning eligible schemes list via the `X/Y` coordinate system on a `Letter` page size, and pipe it directly to the user as an HTTP File Attachment (`send_file`) without ever cluttering the server's hard drive.