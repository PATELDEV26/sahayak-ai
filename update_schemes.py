import pandas as pd
import os

csv_path = 'c:/Users/patel/Desktop/jayan/sahayak_ai/schemes.csv'

# Read existing csv
df = pd.read_csv(csv_path)

# Rename columns
rename_map = {
    'category': 'persona',
    'max_income': 'income_ceiling',
    'caste': 'category',
    'description': 'benefit_desc',
    'apply_link': 'official_url',
    'required_documents': 'required_docs'
}
df = df.rename(columns=rename_map)

# Add new columns if missing
if 'scheme_id' not in df.columns:
    df.insert(0, 'scheme_id', range(1, len(df) + 1))
if 'sub_category' not in df.columns:
    df['sub_category'] = 'All'
if 'authority' not in df.columns:
    df['authority'] = 'Central'
if 'gender' not in df.columns:
    df['gender'] = 'All'

# Reorder columns to have the required ones first (or just keep them)
columns_order = ['scheme_id', 'scheme_name', 'persona', 'sub_category', 'authority', 'gender', 'min_age', 'max_age', 'income_ceiling', 'min_land', 'category', 'state', 'disability_required', 'bpl_required', 'benefit_desc', 'benefit_amount', 'official_url', 'required_docs']

# Keep any other columns that might exist by appending them
for col in df.columns:
    if col not in columns_order:
        columns_order.append(col)

df = df[columns_order]

# Now let's add 5 Others schemes and 5 Girl schemes
new_schemes = [
    {
        'scheme_id': len(df) + 1, 'scheme_name': 'Indira Gandhi National Widow Pension Scheme', 'persona': 'Others', 'sub_category': 'Widow', 'authority': 'Central', 'gender': 'Female', 'min_age': 40, 'max_age': 999, 'income_ceiling': 0, 'min_land': 0.0, 'category': 'All', 'state': 'All', 'disability_required': 'No', 'bpl_required': 'Yes', 'benefit_desc': 'Monthly pension for BPL widows.', 'benefit_amount': 'Rs. 300/month', 'official_url': 'https://nsap.nic.in', 'required_docs': 'Aadhaar, Death Certificate of Husband, BPL Card'
    },
    {
        'scheme_id': len(df) + 2, 'scheme_name': 'Indira Gandhi National Old Age Pension Scheme', 'persona': 'Others', 'sub_category': 'Senior Citizen', 'authority': 'Central', 'gender': 'All', 'min_age': 60, 'max_age': 999, 'income_ceiling': 0, 'min_land': 0.0, 'category': 'All', 'state': 'All', 'disability_required': 'No', 'bpl_required': 'Yes', 'benefit_desc': 'Monthly pension for senior citizens below poverty line.', 'benefit_amount': 'Rs. 200-500/month', 'official_url': 'https://nsap.nic.in', 'required_docs': 'Aadhaar, Age Proof, BPL Card'
    },
    {
        'scheme_id': len(df) + 3, 'scheme_name': 'Integrated Child Development Services (ICDS)', 'persona': 'Others', 'sub_category': 'Child', 'authority': 'Central', 'gender': 'All', 'min_age': 0, 'max_age': 6, 'income_ceiling': 0, 'min_land': 0.0, 'category': 'All', 'state': 'All', 'disability_required': 'No', 'bpl_required': 'No', 'benefit_desc': 'Supplementary nutrition, immunization, and preschool education.', 'benefit_amount': 'Nutrition and Care', 'official_url': 'https://icds-wcd.nic.in', 'required_docs': 'Birth Certificate, Aadhaar'
    },
    {
        'scheme_id': len(df) + 4, 'scheme_name': 'Assistance to Disabled Persons for Purchase of Aids/Appliances', 'persona': 'Others', 'sub_category': 'Person with Disability', 'authority': 'Central', 'gender': 'All', 'min_age': 0, 'max_age': 999, 'income_ceiling': 20000, 'min_land': 0.0, 'category': 'All', 'state': 'All', 'disability_required': 'Yes', 'bpl_required': 'No', 'benefit_desc': 'Assistance for purchasing aids and appliances for PwD.', 'benefit_amount': 'Aids/Appliances', 'official_url': 'https://disabilityaffairs.gov.in', 'required_docs': 'Aadhaar, Disability Certificate, Income Certificate'
    },
    {
        'scheme_id': len(df) + 5, 'scheme_name': 'Naya Savera - Free Coaching and Allied Scheme for Minority', 'persona': 'Others', 'sub_category': 'Minority Community Member', 'authority': 'Central', 'gender': 'All', 'min_age': 15, 'max_age': 30, 'income_ceiling': 600000, 'min_land': 0.0, 'category': 'All', 'state': 'All', 'disability_required': 'No', 'bpl_required': 'No', 'benefit_desc': 'Free coaching for competitive exams for minority students.', 'benefit_amount': 'Free Coaching', 'official_url': 'http://minorityaffairs.gov.in', 'required_docs': 'Aadhaar, Minority Certificate, Income Certificate'
    },
    {
        'scheme_id': len(df) + 6, 'scheme_name': 'Beti Bachao Beti Padhao', 'persona': 'Girl', 'sub_category': 'All', 'authority': 'Central', 'gender': 'Female', 'min_age': 0, 'max_age': 10, 'income_ceiling': 0, 'min_land': 0.0, 'category': 'All', 'state': 'All', 'disability_required': 'No', 'bpl_required': 'No', 'benefit_desc': 'Welfare and education for girl child.', 'benefit_amount': 'Variable', 'official_url': 'https://wcd.nic.in', 'required_docs': 'Aadhaar, Birth Certificate'
    },
    {
        'scheme_id': len(df) + 7, 'scheme_name': 'National Scheme of Incentive to Girls for Secondary Education', 'persona': 'Girl', 'sub_category': 'All', 'authority': 'Central', 'gender': 'Female', 'min_age': 14, 'max_age': 18, 'income_ceiling': 0, 'min_land': 0.0, 'category': 'SC/ST', 'state': 'All', 'disability_required': 'No', 'bpl_required': 'No', 'benefit_desc': 'Incentive to promote secondary education for girls.', 'benefit_amount': 'Rs. 3000 Fixed Deposit', 'official_url': 'https://scholarships.gov.in', 'required_docs': 'Aadhaar, Caste Certificate, School Bonafide'
    },
    {
        'scheme_id': len(df) + 8, 'scheme_name': 'CBSE Udaan', 'persona': 'Girl', 'sub_category': 'All', 'authority': 'Central', 'gender': 'Female', 'min_age': 15, 'max_age': 18, 'income_ceiling': 600000, 'min_land': 0.0, 'category': 'All', 'state': 'All', 'disability_required': 'No', 'bpl_required': 'No', 'benefit_desc': 'Mentoring for girl students in engineering entrance exams.', 'benefit_amount': 'Free Mentoring', 'official_url': 'http://cbse.nic.in', 'required_docs': 'Aadhaar, School Marksheet'
    },
    {
        'scheme_id': len(df) + 9, 'scheme_name': 'Mukhyamantri Kanya Kelavni Nidhi', 'persona': 'Girl', 'sub_category': 'All', 'authority': 'State', 'gender': 'Female', 'min_age': 17, 'max_age': 25, 'income_ceiling': 0, 'min_land': 0.0, 'category': 'All', 'state': 'Gujarat', 'disability_required': 'No', 'bpl_required': 'No', 'benefit_desc': 'Support for girls studying medical courses in Gujarat.', 'benefit_amount': 'Variable Scholarship', 'official_url': 'https://gujarat.gov.in', 'required_docs': 'Aadhaar, Domicile, Admission Letter'
    },
    {
        'scheme_id': len(df) + 10, 'scheme_name': 'Sukanya Samriddhi Yojana', 'persona': 'Girl', 'sub_category': 'All', 'authority': 'Central', 'gender': 'Female', 'min_age': 0, 'max_age': 10, 'income_ceiling': 0, 'min_land': 0.0, 'category': 'All', 'state': 'All', 'disability_required': 'No', 'bpl_required': 'No', 'benefit_desc': 'Small deposit scheme for the girl child.', 'benefit_amount': 'High Interest Savings', 'official_url': 'https://www.indiapost.gov.in', 'required_docs': 'Birth Certificate, Aadhaar of Parent'
    }
]

df = pd.concat([df, pd.DataFrame(new_schemes)], ignore_index=True)

df.to_csv(csv_path, index=False)
print("Schemes successfully updated.")
