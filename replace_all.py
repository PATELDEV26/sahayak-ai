import os

def replace_in_file(filepath, replacements):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    for old, new in replacements:
        content = content.replace(old, new)
        
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

# Update app.py
replace_in_file('app.py', [
    ("def widower_form():", "def girls_form():"),
    ("@app.route('/widower')", "@app.route('/girls')"),
    ("render_template('widower.html')", "render_template('girls.html')")
])

# Update index.html
replace_in_file('templates/index.html', [
    ("Widower/Widow Card", "Girls Card"),
    ("Widow/Widower", "Girls"),
    ("विधवा/विधुर", "लड़कियां"),
    ("widower_form", "girls_form"),
    ("Pension, housing, and social security benefits.", "Scholarships, empowerment, and special schemes for girls."),
    ("पेंशन, आवास और सामाजिक सुरक्षा लाभ।", "लड़कियों के लिए छात्रवृत्ति, सशक्तिकरण और विशेष योजनाएं।"),
    ("🕊️", "👧")
])

# Update girls.html
replace_in_file('templates/girls.html', [
    ("Widow/Widower", "Girls"),
    ("विधवा/विधुर", "लड़कियों का"),
    ("category='widower'", "category='girl'"),
    ("min=\"18\"", "min=\"0\"")
])

print("Replacements complete.")
