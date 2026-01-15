import requests
import pandas as pd
import json
import time
import io
import random
from datetime import datetime, timedelta

# --- הגדרות ---
MIN_MARKET_CAP = 1000000000  # 1 מיליארד דולר
SCAN_DAYS = 90               # 3 חודשים (נתונים אמיתיים בלבד)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://www.nasdaq.com",
    "Referer": "https://www.nasdaq.com/",
}

def normalize_symbol(symbol):
    if not symbol: return ""
    return symbol.strip().upper().replace('.', '-').replace('/', '-').replace('^', '')

def get_sp500_tickers():
    print("1. טוען רשימת S&P 500...")
    try:
        url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        df = pd.read_html(io.StringIO(r.text))[0]
        return set(df['Symbol'].apply(normalize_symbol).tolist())
    except: return set()

def get_nasdaq100_tickers():
    print("2. טוען רשימת Nasdaq 100...")
    try:
        url = 'https://en.wikipedia.org/wiki/NASDAQ-100'
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        tables = pd.read_html(io.StringIO(r.text))
        for t in tables:
            if 'Ticker' in t.columns:
                return set(t['Ticker'].apply(normalize_symbol).tolist())
        return set()
    except: return set()

def get_master_stock_list():
    print("3. בונה קטלוג מניות...")
    url = "https://api.nasdaq.com/api/screener/stocks?tableonly=true&limit=25&offset=0&download=true"
    try:
        r = requests.get(url, headers=HEADERS)
        data = r.json()['data']['rows']
        stock_map = {}
        for row in data:
            try:
                sym = normalize_symbol(row.get('symbol'))
                cap_str = row.get('marketCap')
                cap = 0
                if cap_str and isinstance(cap_str, str) and cap_str != 'NA':
                    clean = cap_str.replace(',', '').replace('$', '').strip()
                    if clean: cap = float(clean)
                
                stock_map[sym] = {
                    "name": row.get('name', ''),
                    "sector": row.get('sector', 'Unknown'),
                    "marketCap": cap
                }
            except: continue
        print(f"   V קטלוג מוכן: {len(stock_map)} מניות.")
        return stock_map
    except: return {}

def fetch_calendar_by_date(date_str, stock_map, sp500, nasdaq100):
    url = f"https://api.nasdaq.com/api/calendar/earnings?date={date_str}"
    try:
        r = requests.get(url, headers=HEADERS)
        data = r.json()
        if data.get('data') is None or data['data'].get('rows') is None: return []

        rows = data['data']['rows']
        valid = []
        for row in rows:
            raw_sym = row.get('symbol')
            sym = normalize_symbol(raw_sym)
            
            if sym in stock_map:
                info = stock_map[sym]
                cap = info['marketCap']
                is_sp500 = sym in sp500
                is_nasdaq100 = sym in nasdaq100
                
                # --- לוגיקה חדשה: שליפת שעת הדיווח ---
                raw_time = row.get('time', 'time-not-supplied')
                report_time = "TBD" # ברירת מחדל
                
                if raw_time == "time-pre-market":
                    report_time = "Before Market"
                elif raw_time == "time-after-hours":
                    report_time = "After Market"
                # -------------------------------------

                if cap >= MIN_MARKET_CAP or is_sp500 or is_nasdaq100:
                    entry = {
                        "symbol": raw_sym,
                        "name": info['name'],
                        "sector": info['sector'],
                        "marketCap": cap,
                        "earningsDate": date_str,
                        "time": report_time,         # השדה החדש
                        "inSp500": is_sp500,
                        "inNasdaq100": is_nasdaq100
                    }
                    valid.append(entry)
        return valid
    except: return []

def main():
    start_time = time.time()
    sp500 = get_sp500_tickers()
    nasdaq100 = get_nasdaq100_tickers()
    stock_map = get_master_stock_list()

    if not stock_map: return

    final_data = []
    print(f"\n4. סורק נתונים ל-{SCAN_DAYS} הימים הקרובים...")
    
    today = datetime.now()
    dates_to_check = [ (today + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(SCAN_DAYS) ]
    
    for i, date_str in enumerate(dates_to_check):
        print(f"\r   סורק: {date_str} | נאספו: {len(final_data)}", end="")
        earnings = fetch_calendar_by_date(date_str, stock_map, sp500, nasdaq100)
        final_data.extend(earnings)
        time.sleep(0.15)

    print("\n")
    final_data.sort(key=lambda x: x['earningsDate'])
    
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(final_data, f, ensure_ascii=False, indent=4)

    print(f"בוצע! נשמרו {len(final_data)} דוחות (כולל זמני דיווח).")
    print(f"זמן ריצה: {time.time() - start_time:.2f} שניות")

if __name__ == "__main__":
    main()