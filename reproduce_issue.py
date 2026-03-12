import sys
import os

# Add current directory to sys.path to allow import
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import load_schemes

try:
    print("Testing load_schemes from app.py...")
    df = load_schemes()
    if df.empty:
        print("load_schemes returned empty DataFrame! Validation Failed.")
    else:
        print("load_schemes success. DataFrame shape:", df.shape)
        print("Columns:", df.columns.tolist())
        
        category = 'student'
        if 'category' in df.columns:
            category_df = df[df['category'].str.lower() == category.lower()]
            print("Category filtering success")
        else:
            print("Error: 'category' column missing!")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
