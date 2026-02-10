# GFC Financial Chatbot Prototype (Rule-Based)

## Overview
This prototype chatbot provides deterministic, data-backed answers to common financial questions using structured 10-K metrics for Apple, Microsoft, and Tesla (last three fiscal years). It is intentionally simplified to meet time constraints and emphasize rule-based logic, accuracy, and explainability.

## Data Source
- Input file: `GFC_10K_Financial_Data_3_Years.csv`
- Metrics supported (USD millions):
  - Total Revenue
  - Net Income
  - Total Assets
  - Total Liabilities
  - Cash Flow from Operating Activities (CFO)
- The chatbot computes Year-over-Year (YoY) % changes internally for supported metrics.

## How it works (high level)
1. Loads the CSV into a pandas DataFrame.
2. Parses the user query using rule-based keyword matching to detect:
   - company (Apple/Microsoft/Tesla)
   - metric (revenue, net income/profit, assets, liabilities, CFO)
   - fiscal year (optional; defaults to latest available for the company)
   - YoY intent (optional: words like “change”, “growth”, “YoY”)
   - compare intent (optional: “compare”, “vs”)
3. Retrieves the relevant data point(s) and returns a concise natural-language response.

## Example queries (supported)
- “What was Apple revenue in 2024?”
- “How did Tesla net income change in 2024?”
- “What is Microsoft CFO in 2024?”
- “Compare Apple and Microsoft revenue in 2024”
- “Compare revenue growth for all companies”

## Limitations
- Rule-based keyword parsing: phrasing must include recognizable metric/company keywords.
- Limited scope: only the listed metrics and companies are supported.
- No advanced NLP or ML learning (prototype scope).

## Run
Install:
- `pip install pandas`

Run:
- `python chatbot.py`
