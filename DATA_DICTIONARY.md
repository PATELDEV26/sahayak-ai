# SahayakAI — Scheme Database Data Dictionary

This document details the schema, allowed values, units, and validation rules for `schemes.csv` (used by the SahayakAI scheme matching engine).

## Table Schema (14 Columns)

| # | Column Name | Data Type | Description | Allowed Values / Validation Rules |
|---|---|---|---|---|
| 1 | `scheme_name` | String | Official name of the government scheme or scholarship | Must be non-empty string |
| 2 | `category` | String | Target beneficiary persona category | `Student`, `Farmer`, `Widower` |
| 3 | `min_age` | Integer | Minimum qualifying age in years | Integer $\ge 0$ |
| 4 | `max_age` | Integer | Maximum qualifying age in years | Integer $\ge min\_age$ |
| 5 | `max_income` | Float | Annual household income ceiling in INR | Float $\ge 0$ (`0` indicates no income ceiling) |
| 6 | `min_land` | Float | Minimum agricultural land owned in Acres (Farmers) | Float $\ge 0$ |
| 7 | `caste` | String | Target caste or social category | `All`, `General`, `SC`, `ST`, `OBC` |
| 8 | `state` | String | Geographical eligibility coverage | `All` (Pan-India) or Indian State/UT name (e.g., `Gujarat`) |
| 9 | `disability_required`| String | Whether physical disability is mandatory | `Yes` or `No` |
| 10 | `bpl_required` | String | Whether Below Poverty Line status is mandatory | `Yes` or `No` |
| 11 | `description` | String | Detailed human-readable description of the scheme | Non-empty text |
| 12 | `benefit_amount` | String | Summary of financial or in-kind benefits | Non-empty text |
| 13 | `apply_link` | String | Official portal URL to apply | Valid URL starting with `https://` or `http://` |
| 14 | `required_documents` | String | Semicolon-separated list of mandatory documents | E.g., `Aadhaar;Income Certificate;7/12 Land Record` |

## Validation Policy
Any row violating the above integrity constraints will be flagged by `validate_schemes.py` to prevent silent corrupted filtering in Pandas.
