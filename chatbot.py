import re
import pandas as pd
from pathlib import Path

DATA_FILE = "GFC_10K_Financial_Data_3_Years.csv"
SUPPORTED_COMPANIES = ["Apple", "Microsoft", "Tesla"]


# -----------------------------
# Load + prepare data
# -----------------------------
def load_data(path: str) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Missing file: {path} (put it next to chatbot.py)")

    df = pd.read_csv(p)

    # Rename if your CSV came from Excel headers
    col_map = {
        "Fiscal Year": "FiscalYear",
        "Total Revenue (USD mn)": "TotalRevenue",
        "Net Income (USD mn)": "NetIncome",
        "Total Assets (USD mn)": "TotalAssets",
        "Total Liabilities (USD mn)": "TotalLiabilities",
        "Cash Flow from Operations (USD mn)": "CFO",
    }
    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

    required = ["Company", "FiscalYear", "TotalRevenue", "NetIncome", "TotalAssets", "TotalLiabilities", "CFO"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"CSV missing required columns: {missing}")

    df["FiscalYear"] = pd.to_numeric(df["FiscalYear"], errors="raise").astype(int)
    for c in ["TotalRevenue", "NetIncome", "TotalAssets", "TotalLiabilities", "CFO"]:
        df[c] = pd.to_numeric(df[c], errors="raise")

    df = df.sort_values(["Company", "FiscalYear"]).reset_index(drop=True)

    # Safe YoY columns
    for c in ["TotalRevenue", "NetIncome", "TotalAssets", "TotalLiabilities", "CFO"]:
        df[f"{c}_YoY_pct"] = df.groupby("Company")[c].pct_change() * 100

    return df


def money_musd(x) -> str:
    return f"{x:,.0f} USD mn"


def latest_year(df: pd.DataFrame, company: str) -> int:
    return int(df[df["Company"] == company]["FiscalYear"].max())


def get_row(df: pd.DataFrame, company: str, year: int) -> pd.Series:
    sub = df[(df["Company"] == company) & (df["FiscalYear"] == year)]
    if sub.empty:
        raise KeyError(f"No data for {company} in FY{year}")
    return sub.iloc[0]


# -----------------------------
# “Intelligent” rule parsing
# -----------------------------
def extract_companies(text: str):
    t = text.lower()
    found = []
    for c in SUPPORTED_COMPANIES:
        if c.lower() in t:
            found.append(c)
    return found


def extract_year(text: str):
    m = re.search(r"\b(20\d{2})\b", text)
    return int(m.group(1)) if m else None


def detect_metric(text: str):
    t = text.lower()

    # metric -> (column, friendly name)
    if any(k in t for k in ["revenue", "sales", "top line"]):
        return ("TotalRevenue", "total revenue")
    if any(k in t for k in ["net income", "profit", "earnings"]):
        return ("NetIncome", "net income")
    if any(k in t for k in ["assets", "total assets"]):
        return ("TotalAssets", "total assets")
    if any(k in t for k in ["liabilities", "total liabilities", "debt"]):
        return ("TotalLiabilities", "total liabilities")
    if any(k in t for k in ["cfo", "operating cash", "operating cash flow", "cash flow from operations"]):
        return ("CFO", "cash flow from operations (CFO)")

    return (None, None)


def wants_yoy(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in ["yoy", "year over year", "growth", "change", "increased", "decreased", "delta"])


def wants_compare(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in ["compare", "vs", "versus", "difference", "which company"])


# -----------------------------
# Response generation
# -----------------------------
def answer_single(df: pd.DataFrame, company: str, metric_col: str, metric_name: str, year: int, include_yoy: bool) -> str:
    r = get_row(df, company, year)
    value = r[metric_col]

    msg = f"{company} {metric_name} (FY{year}) = {money_musd(value)}."

    if include_yoy:
        yoy_col = f"{metric_col}_YoY_pct"
        yoy = r[yoy_col]
        if pd.isna(yoy):
            msg += " YoY: N/A (no prior year in dataset)."
        else:
            direction = "increased" if yoy > 0 else "decreased"
            msg += f" YoY: {direction} by {abs(yoy):.2f}% vs FY{year-1}."

    return msg


def answer_compare(df: pd.DataFrame, companies, metric_col: str, metric_name: str, year: int, include_yoy: bool) -> str:
    parts = []
    for c in companies:
        try:
            parts.append(answer_single(df, c, metric_col, metric_name, year, include_yoy))
        except KeyError:
            parts.append(f"{c}: No data for FY{year}.")
    return " | ".join(parts)


def chatbot_reply(df: pd.DataFrame, user_text: str, state: dict) -> str:
    text = user_text.strip()

    # Update state with company if mentioned
    companies = extract_companies(text)
    if companies:
        state["last_companies"] = companies

    year = extract_year(text)
    metric_col, metric_name = detect_metric(text)
    include_yoy = wants_yoy(text)
    compare = wants_compare(text) or (len(companies) > 1)

    # If metric missing, ask a short clarifying question
    if metric_col is None:
        return "Which metric do you want: revenue, net income, assets, liabilities, or operating cash flow (CFO)?"

    # If no company mentioned, fallback to last referenced, else ask
    if not companies:
        companies = state.get("last_companies", [])
    if not companies:
        return "Which company: Apple, Microsoft, or Tesla? (You can also say 'compare all')"

    # Support: “compare all”
    if "all" in text.lower() or "all companies" in text.lower():
        companies = SUPPORTED_COMPANIES
        compare = True

    # Default year = latest year for the first company mentioned
    if year is None:
        year = latest_year(df, companies[0])

    # If compare requested, compare across companies
    if compare:
        # if user said compare but only one company, compare all companies
        if len(companies) == 1:
            companies = SUPPORTED_COMPANIES
        return answer_compare(df, companies, metric_col, metric_name, year, include_yoy)

    # Otherwise single company answer
    return answer_single(df, companies[0], metric_col, metric_name, year, include_yoy)


def main():
    df = load_data(DATA_FILE)
    state = {"last_companies": []}

    print("=== GFC Financial Chatbot (Rule-Based Prototype) ===")
    print("Ask naturally, e.g.:")
    print("- What was Apple revenue in 2024?")
    print("- How did Tesla net income change in 2024?")
    print("- Compare Microsoft and Apple CFO in 2024")
    print("- Compare revenue growth for all companies\n")
    print("Type 'exit' to quit.\n")

    while True:
        user = input("You: ").strip()
        if user.lower() == "exit":
            print("Bot: Goodbye.")
            break
        try:
            print("Bot:", chatbot_reply(df, user, state), "\n")
        except Exception as e:
            print(f"Bot: Error: {e}\n")


if __name__ == "__main__":
    main()
