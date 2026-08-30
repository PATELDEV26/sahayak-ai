#!/usr/bin/env python3
"""
SahayakAI — Eligibility Engine Accuracy & Edge-Case Benchmark Suite
Runs 30 comprehensive test profiles against the 105+ schemes database
and verifies precision, recall, and edge-case handling.
"""

import os
import sys
import pandas as pd
from app import evaluate_schemes_for_profile

def run_eligibility_test_suite():
    csv_path = "schemes.csv" if os.path.exists("schemes.csv") else os.path.join(os.path.dirname(__file__), "schemes.csv")
    df = pd.read_csv(csv_path)

    print("==========================================================")
    print("      SahayakAI Eligibility Matching Benchmark Suite      ")
    print("==========================================================")
    print(f"Loaded database: {len(df)} schemes")

    # Define 30 Test Profiles with edge cases and assertions
    test_profiles = [
        # ── Students (10 Profiles) ─────────────────────────────────────────────
        {
            "id": "ST-01", "name": "General Gujarat Undergraduate (Age 19, Income 3L)",
            "profile": {"category": "student", "age": 19, "income": 300000, "state": "Gujarat", "caste": "General", "disability": "No"},
            "must_include": ["Central Sector Scholarship Scheme", "Mukhyamantri Yuva Swavalamban Yojana (MYSY)"],
            "must_exclude": ["Post-Matric Scholarship for SC Students"]
        },
        {
            "id": "ST-02", "name": "SC Gujarat College Student (Age 20, Income 2L)",
            "profile": {"category": "student", "age": 20, "income": 200000, "state": "Gujarat", "caste": "SC", "disability": "No"},
            "must_include": ["Post-Matric Scholarship for SC Students", "Digital Gujarat Post Matric Scholarship SC", "Central Sector Scholarship Scheme"],
            "must_exclude": ["Post-Matric Scholarship for ST Students"]
        },
        {
            "id": "ST-03", "name": "ST Tribal School Student (Age 14, Income 1.5L)",
            "profile": {"category": "student", "age": 14, "income": 150000, "state": "Gujarat", "caste": "ST", "disability": "No"},
            "must_include": ["Pre-Matric Scholarship for SC and ST Students", "Uniform Assistance Scheme SC ST Gujarat"],
            "must_exclude": ["Shodh Doctoral Fellowship Scheme Gujarat"]
        },
        {
            "id": "ST-04", "name": "Differently-Abled Technical Student (Age 21, Income 4L)",
            "profile": {"category": "student", "age": 21, "income": 400000, "state": "All", "caste": "General", "disability": "Yes"},
            "must_include": ["Saksham Scholarship Scheme for Differently-Abled"],
            "must_exclude": []
        },
        {
            "id": "ST-05", "name": "Non-Disabled Student checking Disability Scheme exclusion",
            "profile": {"category": "student", "age": 21, "income": 400000, "state": "All", "caste": "General", "disability": "No"},
            "must_include": ["Central Sector Scholarship Scheme"],
            "must_exclude": ["Saksham Scholarship Scheme for Differently-Abled"]
        },
        {
            "id": "ST-06", "name": "PhD Scholar Gujarat (Age 27, Income 0)",
            "profile": {"category": "student", "age": 27, "income": 0, "state": "Gujarat", "caste": "General", "disability": "No"},
            "must_include": ["Shodh Doctoral Fellowship Scheme Gujarat"],
            "must_exclude": ["National Means-Cum-Merit Scholarship"]
        },
        {
            "id": "ST-07", "name": "Over-age Student (Age 38, checking age cutoff)",
            "profile": {"category": "student", "age": 38, "income": 100000, "state": "Gujarat", "caste": "General", "disability": "No"},
            "must_include": [],
            "must_exclude": ["Mukhyamantri Yuva Swavalamban Yojana (MYSY)", "Central Sector Scholarship Scheme"]
        },
        {
            "id": "ST-08", "name": "High Income Student (Income 15L, checking income ceiling exclusion)",
            "profile": {"category": "student", "age": 19, "income": 1500000, "state": "Gujarat", "caste": "General", "disability": "No"},
            "must_include": [],
            "must_exclude": ["Central Sector Scholarship Scheme", "Mukhyamantri Yuva Swavalamban Yojana (MYSY)"]
        },
        {
            "id": "ST-09", "name": "OBC Student Maharashtra (Age 19, Income 2L)",
            "profile": {"category": "student", "age": 19, "income": 200000, "state": "Maharashtra", "caste": "OBC", "disability": "No"},
            "must_include": ["Post-Matric Scholarship for OBC Students", "Central Sector Scholarship Scheme"],
            "must_exclude": ["Digital Gujarat Post Matric Scholarship SEBC OBC"]
        },
        {
            "id": "ST-10", "name": "EWS Student Gujarat (Age 19, Income 5L)",
            "profile": {"category": "student", "age": 19, "income": 500000, "state": "Gujarat", "caste": "General", "disability": "No"},
            "must_include": ["Higher Education Scheme for EWS Students"],
            "must_exclude": ["Post-Matric Scholarship for SC Students"]
        },

        # ── Farmers (10 Profiles) ──────────────────────────────────────────────
        {
            "id": "FM-01", "name": "Small Landholding Farmer Gujarat (Age 45, Land 1.5 Acres)",
            "profile": {"category": "farmer", "age": 45, "income": 120000, "state": "Gujarat", "land_owned": 1.5},
            "must_include": ["PM-KISAN Samman Nidhi", "Pradhan Mantri Fasal Bima Yojana PMFBY", "Mukhyamantri Kisan Sahay Yojana Gujarat"],
            "must_exclude": ["Barbed Wire Fencing Assistance Scheme Gujarat"] # requires min 2 acres
        },
        {
            "id": "FM-02", "name": "Large Farmer Gujarat (Age 50, Land 5.0 Acres)",
            "profile": {"category": "farmer", "age": 50, "income": 400000, "state": "Gujarat", "land_owned": 5.0},
            "must_include": ["PM-KISAN Samman Nidhi", "Barbed Wire Fencing Assistance Scheme Gujarat", "Kisan Drone Subsidy Scheme"],
            "must_exclude": []
        },
        {
            "id": "FM-03", "name": "Landless / Micro Land Farmer (Age 30, Land 0.05 Acres)",
            "profile": {"category": "farmer", "age": 30, "income": 80000, "state": "Gujarat", "land_owned": 0.05},
            "must_include": ["PM-KISAN Samman Nidhi"],
            "must_exclude": ["Sub-Mission on Agricultural Mechanization SMAM"] # min_land 1.0
        },
        {
            "id": "FM-04", "name": "Young Farmer checking Pension Age cutoff (Age 25)",
            "profile": {"category": "farmer", "age": 25, "income": 90000, "state": "All", "land_owned": 2.0},
            "must_include": ["PM Kisan Maan Dhan Yojana PM-KMY"],
            "must_exclude": []
        },
        {
            "id": "FM-05", "name": "Senior Farmer above PM-KMY age cutoff (Age 55)",
            "profile": {"category": "farmer", "age": 55, "income": 90000, "state": "All", "land_owned": 2.0},
            "must_include": ["PM-KISAN Samman Nidhi"],
            "must_exclude": ["PM Kisan Maan Dhan Yojana PM-KMY"] # max age 40
        },
        {
            "id": "FM-06", "name": "Tribal Organic Farmer Dang Gujarat (ST, Land 1.0 Acres)",
            "profile": {"category": "farmer", "age": 40, "income": 100000, "state": "Gujarat", "caste": "ST", "land_owned": 1.0},
            "must_include": ["Organic Farming Subsidy Tribal Farmers Gujarat", "Paramparagat Krishi Vikas Yojana PKVY"],
            "must_exclude": []
        },
        {
            "id": "FM-07", "name": "Non-Tribal Farmer checking Tribal Organic exclusion (General, Land 1.0)",
            "profile": {"category": "farmer", "age": 40, "income": 100000, "state": "Gujarat", "caste": "General", "land_owned": 1.0},
            "must_include": ["Paramparagat Krishi Vikas Yojana PKVY"],
            "must_exclude": ["Organic Farming Subsidy Tribal Farmers Gujarat"]
        },
        {
            "id": "FM-08", "name": "Farmer outside Gujarat checking state exclusion (Punjab)",
            "profile": {"category": "farmer", "age": 40, "income": 150000, "state": "Punjab", "land_owned": 2.0},
            "must_include": ["PM-KISAN Samman Nidhi", "Pradhan Mantri Fasal Bima Yojana PMFBY"],
            "must_exclude": ["Mukhyamantri Kisan Sahay Yojana Gujarat", "i-Khedut Farm Mechanization Subsidy Gujarat"]
        },
        {
            "id": "FM-09", "name": "Senior Farmer Age 85 (checking upper age tolerance)",
            "profile": {"category": "farmer", "age": 85, "income": 100000, "state": "Gujarat", "land_owned": 2.0},
            "must_include": ["PM-KISAN Samman Nidhi"],
            "must_exclude": ["Kisan Credit Card KCC Scheme"] # max age 75
        },
        {
            "id": "FM-10", "name": "Marginal Farmer checking Tool Kit eligibility (Land 0.5 Acres)",
            "profile": {"category": "farmer", "age": 35, "income": 90000, "state": "Gujarat", "land_owned": 0.5},
            "must_include": ["Agricultural Tool Kit Assistance Marginal Farmers"],
            "must_exclude": []
        },

        # ── Widows / Widowers (10 Profiles) ────────────────────────────────────
        {
            "id": "WD-01", "name": "BPL Senior Widow Gujarat (Age 65, BPL Yes, Income 40000)",
            "profile": {"category": "widower", "age": 65, "income": 40000, "state": "Gujarat", "bpl": "Yes"},
            "must_include": ["Indira Gandhi National Widow Pension IGNWPS", "Ganga Swaroopa Yojana Gujarat Widow Pension", "PM Ujjwala Yojana Free LPG Connection"],
            "must_exclude": []
        },
        {
            "id": "WD-02", "name": "Non-BPL Widow Gujarat (Age 45, BPL No, Income 90000)",
            "profile": {"category": "widower", "age": 45, "income": 90000, "state": "Gujarat", "bpl": "No"},
            "must_include": ["Ganga Swaroopa Yojana Gujarat Widow Pension"],
            "must_exclude": ["Indira Gandhi National Widow Pension IGNWPS", "PM Ujjwala Yojana Free LPG Connection"]
        },
        {
            "id": "WD-03", "name": "Young Widow checking Remarriage Sahay eligibility (Age 28)",
            "profile": {"category": "widower", "age": 28, "income": 80000, "state": "Gujarat", "bpl": "No"},
            "must_include": ["Ganga Swaroopa Punah Lagna Sahay Remarriage", "Silai Machine Assistance Scheme for Widows"],
            "must_exclude": ["National Social Assistance Programme NSAP"] # age 60+
        },
        {
            "id": "WD-04", "name": "Widow outside Gujarat (Age 50, Maharashtra, BPL Yes)",
            "profile": {"category": "widower", "age": 50, "income": 60000, "state": "Maharashtra", "bpl": "Yes"},
            "must_include": ["Indira Gandhi National Widow Pension IGNWPS", "Pradhan Mantri Awas Yojana Gramin PMAY-G"],
            "must_exclude": ["Ganga Swaroopa Yojana Gujarat Widow Pension"]
        },
        {
            "id": "WD-05", "name": "SC Widow Gujarat checking Ambedkar Housing (Age 45, SC)",
            "profile": {"category": "widower", "age": 45, "income": 90000, "state": "Gujarat", "caste": "SC", "bpl": "No"},
            "must_include": ["Dr Ambedkar Awas Yojana Gujarat SC Housing", "Pandit Deendayal Upadhyay Awas Yojana Gujarat"],
            "must_exclude": []
        },
        {
            "id": "WD-06", "name": "Senior Citizen Widow checking Annapurna Food Scheme (Age 68)",
            "profile": {"category": "widower", "age": 68, "income": 50000, "state": "All", "bpl": "No"},
            "must_include": ["Annapurna Food Scheme for Senior Citizens"],
            "must_exclude": ["Atal Pension Yojana APY"] # max age 40
        },
        {
            "id": "WD-07", "name": "Widow checking Daughter Marriage Kanyadan Sahay (Age 48)",
            "profile": {"category": "widower", "age": 48, "income": 100000, "state": "Gujarat", "bpl": "No"},
            "must_include": ["Widow Daughter Marriage Aid Kanyadan Sahay"],
            "must_exclude": []
        },
        {
            "id": "WD-08", "name": "Young Widow checking Sukanya Samriddhi & PM SVANidhi (Age 30)",
            "profile": {"category": "widower", "age": 30, "income": 120000, "state": "All", "bpl": "No"},
            "must_include": ["Sukanya Samriddhi Yojana Daughter Support", "PM SVANidhi Street Vendor Support"],
            "must_exclude": ["Indira Gandhi National Widow Pension IGNWPS"]
        },
        {
            "id": "WD-09", "name": "Destitute Widow checking Vocational Training Subsidy (Age 35)",
            "profile": {"category": "widower", "age": 35, "income": 80000, "state": "Gujarat", "bpl": "No"},
            "must_include": ["Destitute Women Vocational Training Subsidy", "GWEDC Microcredit Loan for Single Women"],
            "must_exclude": []
        },
        {
            "id": "WD-10", "name": "High Income Widow checking exclusion above income limit (Income 6L)",
            "profile": {"category": "widower", "age": 45, "income": 600000, "state": "Gujarat", "bpl": "No"},
            "must_include": [],
            "must_exclude": ["Ganga Swaroopa Yojana Gujarat Widow Pension", "Indira Gandhi National Widow Pension IGNWPS"]
        }
    ]

    total_tests = len(test_profiles)
    passed_tests = 0
    total_expected = 0
    total_retrieved = 0
    true_positives = 0

    print(f"\nRunning {total_tests} Edge-Case Profiles...")
    print("-" * 75)

    for case in test_profiles:
        profile = case["profile"]
        matches = evaluate_schemes_for_profile(df, profile)
        matched_names = [m["scheme_name"] for m in matches]

        inc_pass = all(s in matched_names for s in case["must_include"])
        exc_pass = all(s not in matched_names for s in case["must_exclude"])

        is_passed = inc_pass and exc_pass
        status = "PASS" if is_passed else "FAIL"
        if is_passed:
            passed_tests += 1
        else:
            print(f"[FAIL] {case['id']}: {case['name']}")
            for s in case["must_include"]:
                if s not in matched_names:
                    print(f"   Missing expected: '{s}'")
            for s in case["must_exclude"]:
                if s in matched_names:
                    print(f"   Unexpectedly included: '{s}'")

        # Precision & Recall tracking for must_include items
        for s in case["must_include"]:
            total_expected += 1
            if s in matched_names:
                true_positives += 1

    precision = round((passed_tests / total_tests) * 100.0, 1)
    recall = round((true_positives / max(total_expected, 1)) * 100.0, 1)

    print("-" * 75)
    print(f"Test Suite Summary:")
    print(f"  - Total Profiles Evaluated : {total_tests}")
    print(f"  - Profiles Passed          : {passed_tests} / {total_tests} ({precision}%)")
    print(f"  - Core Expectation Recall  : {true_positives} / {total_expected} ({recall}%)")
    print("==========================================================")

    if passed_tests == total_tests:
        print("[SUCCESS] All 30 Eligibility Edge-Case Tests PASSED with 100% Accuracy.")
        return True
    return False

if __name__ == "__main__":
    success = run_eligibility_test_suite()
    sys.exit(0 if success else 1)
