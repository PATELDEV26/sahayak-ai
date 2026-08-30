#!/usr/bin/env python3
"""
SahayakAI — Scheme Database Validator
Checks schemes.csv against strict data quality and integrity constraints.
"""

import os
import sys
import pandas as pd

def validate_schemes(csv_path="schemes.csv"):
    if not os.path.exists(csv_path):
        print(f"[ERROR] Database file not found: {csv_path}")
        return False

    df = pd.read_csv(csv_path)
    total_rows = len(df)
    print("==========================================================")
    print(f"       SahayakAI Scheme Database Audit Report             ")
    print("==========================================================")
    print(f"Loaded database: {csv_path} ({total_rows} schemes)")

    required_cols = [
        "scheme_name", "category", "min_age", "max_age", "max_income",
        "min_land", "caste", "state", "disability_required", "bpl_required",
        "description", "benefit_amount", "apply_link", "required_documents"
    ]

    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        print(f"[FAIL] Missing columns in schemes.csv: {missing_cols}")
        return False

    errors = []

    for idx, row in df.iterrows():
        row_num = idx + 2  # 1-indexed header + 1
        name = row.get("scheme_name", f"Row {row_num}")

        # Check non-empty strings
        for field in ["scheme_name", "category", "description", "benefit_amount", "apply_link"]:
            val = str(row.get(field, "")).strip()
            if not val or val == "nan":
                errors.append(f"Row {row_num} ('{name}'): Empty required field '{field}'")

        # Category check
        cat = str(row.get("category", "")).strip()
        if cat not in ["Student", "Farmer", "Widower"]:
            errors.append(f"Row {row_num} ('{name}'): Invalid category '{cat}'")

        # Numeric bounds check
        try:
            min_age = int(row["min_age"])
            max_age = int(row["max_age"])
            if min_age < 0 or max_age < min_age:
                errors.append(f"Row {row_num} ('{name}'): Invalid age range [{min_age}, {max_age}]")
        except Exception:
            errors.append(f"Row {row_num} ('{name}'): Non-integer age values")

        try:
            max_income = float(row["max_income"])
            if max_income < 0:
                errors.append(f"Row {row_num} ('{name}'): Negative max_income ({max_income})")
        except Exception:
            errors.append(f"Row {row_num} ('{name}'): Invalid numeric max_income")

        try:
            min_land = float(row["min_land"])
            if min_land < 0:
                errors.append(f"Row {row_num} ('{name}'): Negative min_land ({min_land})")
        except Exception:
            errors.append(f"Row {row_num} ('{name}'): Invalid numeric min_land")

    category_counts = df["category"].value_counts().to_dict()
    print("\nCategory Breakdown:")
    for cat, count in category_counts.items():
        print(f"  - {cat}: {count} schemes")

    print(f"\nTotal Errors Found: {len(errors)}")
    if errors:
        for err in errors[:10]:
            print(f"  [X] {err}")
        return False

    print("\n[SUCCESS] All database health checks PASSED (100% Valid Schemes).")
    print("==========================================================\n")
    return True

if __name__ == "__main__":
    success = validate_schemes("schemes.csv") if os.path.exists("schemes.csv") else validate_schemes(os.path.join(os.path.dirname(__file__), "schemes.csv"))
    sys.exit(0 if success else 1)
