import os
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, session, send_file
from werkzeug.utils import secure_filename
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from datetime import datetime
import io

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

@app.route('/widower')
def widower_form():
    return render_template('widower.html')

def save_uploaded_files(files):
    saved_files_count = 0
    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            saved_files_count += 1
    return saved_files_count

@app.route('/check/<category>', methods=['POST'])
def check_eligibility(category):
    if request.method == 'POST':
        form_data = request.form.to_dict()
        files = request.files.getlist('documents')
        
        # Save files
        saved_count = save_uploaded_files(files)
        
        # Determine eligibility using Pandas
        df = load_schemes()
        eligible_schemes = []

        # Common fields
        name = form_data.get('full_name')
        age = int(form_data.get('age', 0))
        income = float(form_data.get('income', 0))
        state = form_data.get('state', 'All')
        
        # Filter by Category and generic rules first
        category_df = df[df['category'].str.lower() == category.lower()]
        
        # 1. State Filter (Match user state or 'All')
        # Note: In a real app, state matching would be more robust
        state_mask = (category_df['state'] == 'All') | (category_df['state'] == state)
        
        # 2. Age Filter
        age_mask = (category_df['min_age'] <= age) & (category_df['max_age'] >= age)
        
        # 3. Income Filter (Scheme max income should be >= User income, or 0 if no limit)
        # If scheme max_income is 0, we assume no upper limit or handled via logic. 
        # But in our CSV, 0 might mean strictly 0? Let's assume income limit 0 implies no specific limit or check logic.
        # Actually, for simplicity, let's assume if max_income in CSV is 0, it ignores income check, 
        # OTHERWISE user income must be <= scheme max_income.
        def income_check(row):
            limit = row['max_income']
            if limit == 0: return True 
            return income <= limit

        # Apply basic filters
        filtered_df = category_df[state_mask & age_mask]
        
        # Apply row-by-row custom logic for specific headers
        matches = []
        for index, row in filtered_df.iterrows():
            if not income_check(row):
                continue
                
            # Category specific logic
            if category == 'student':
                caste = form_data.get('caste', 'General')
                disability = form_data.get('disability', 'No')
                
                # Check Caste: Scheme caste 'General' usually implies open for all, or specific check needed.
                # Simplified: If scheme caste is not 'General' and 'All', it must match user caste.
                # If scheme says 'SC', user must be 'SC'.
                # If scheme says 'General', we assume it's open (or we strictly match). 
                # Let's assume 'General' in CSV means Open for all in this context or matches General.
                # A better logic:
                if row['caste'] not in ['All', 'General'] and row['caste'] != caste:
                    continue
                
                # Disability check
                if row['disability_required'] == 'Yes' and disability == 'No':
                    continue

            elif category == 'farmer':
                land_owned = float(form_data.get('land_owned', 0))
                # If scheme has min_land requirement
                if row['min_land'] > 0 and land_owned < row['min_land']:
                    continue
                
            elif category == 'widower':
                bpl_status = form_data.get('bpl', 'No')
                if row['bpl_required'] == 'Yes' and bpl_status == 'No':
                    continue

            matches.append(row.to_dict())

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

if __name__ == '__main__':
    app.run(debug=True)
