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
import json
from PIL import Image
import google.generativeai as genai

INDIAN_STATES = [
    "Andhra Pradesh","Arunachal Pradesh","Assam","Bihar","Chhattisgarh",
    "Goa","Gujarat","Haryana","Himachal Pradesh","Jharkhand","Karnataka",
    "Kerala","Madhya Pradesh","Maharashtra","Manipur","Meghalaya","Mizoram",
    "Nagaland","Odisha","Punjab","Rajasthan","Sikkim","Tamil Nadu","Telangana",
    "Tripura","Uttar Pradesh","Uttarakhand","West Bengal","Delhi","Jammu",
    "Jammu and Kashmir","Ladakh","Puducherry"
]

def call_gemini_vision(image_bytes, prompt, expected_keys):
    try:
        pil_img = Image.open(io.BytesIO(image_bytes))
        api_key = os.environ.get('GEMINI_VISION_API_KEY') or os.environ.get('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_VISION_API_KEY is not set.")
        genai.configure(api_key=api_key)
        
        model = genai.GenerativeModel('gemini-3.5-flash')
        full_prompt = f"{prompt}\n\nReturn ONLY a valid JSON object with the following keys, and nothing else (do not include ```json wrappers). If a value is missing, return an empty string. Translate all names to English. Format dates as DD/MM/YYYY. Keys: " + ", ".join(expected_keys)
        
        response = model.generate_content([full_prompt, pil_img])
        text = response.text.strip()
        
        if text.startswith('```json'):
            text = text[7:]
        elif text.startswith('```'):
            text = text[3:]
        if text.endswith('```'):
            text = text[:-3]
            
        data = json.loads(text.strip())
        
        result = {}
        for key in expected_keys:
            result[key] = data.get(key, "")
        
        result["confidence"] = "high"
        return result
    except Exception as e:
        print(f"Gemini OCR Error: {e}")
        res = {k: "" for k in expected_keys}
        res["confidence"] = "low"
        return res

def extract_aadhaar_data(image_bytes):
    expected = ["full_name", "date_of_birth", "gender", "aadhaar_last4", "address_state"]
    prompt = "Extract the following details from this Aadhaar card or identity document. For gender, use 'Male' or 'Female'. For aadhaar_last4, extract only the last 4 digits of the Aadhaar number. For address_state, extract the Indian state name."
    result = call_gemini_vision(image_bytes, prompt, expected)
    result["detected_language"] = "eng"
    return result

def extract_income_certificate_data(image_bytes):
    expected = ["income", "full_name", "address_state"]
    prompt = "Extract the annual income amount as a raw number (no currency symbols or commas), the full name of the applicant, and the Indian state name from this income certificate."
    result = call_gemini_vision(image_bytes, prompt, expected)
    try:
        result["income"] = float(result["income"]) if result["income"] else ""
    except ValueError:
        result["income"] = ""
    return result

def extract_land_document_data(image_bytes):
    expected = ["land_owned", "address_state"]
    prompt = "Extract the total land area owned converted to acres (as a number only), and the Indian state name from this land document or 7/12 extract."
    result = call_gemini_vision(image_bytes, prompt, expected)
    try:
        result["land_owned"] = float(result["land_owned"]) if result["land_owned"] else ""
    except ValueError:
        result["land_owned"] = ""
    return result

def extract_death_certificate_data(image_bytes):
    expected = ["full_name", "gender", "death_date", "address_state"]
    prompt = "Extract the full name of the deceased, their gender ('Male' or 'Female'), the date of death (DD/MM/YYYY), and the Indian state name from this death certificate."
    result = call_gemini_vision(image_bytes, prompt, expected)
    return result

def extract_bpl_card_data(image_bytes):
    expected = ["bpl", "address_state"]
    prompt = "Determine if this is a BPL (Below Poverty Line) or ration card. If yes, set 'bpl' to 'Yes'. Also extract the Indian state name."
    result = call_gemini_vision(image_bytes, prompt, expected)
    if result["bpl"] and str(result["bpl"]).lower() in ["yes", "true", "1", "bpl"]:
        result["bpl"] = "Yes"
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
