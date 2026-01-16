import yfinance as yf
import json
import time
import datetime
from datetime import timedelta

# --- הגדרות ---
# כדי לא להעמיס, נסרוק טווח קצר יותר או רק מניות גדולות
SCAN_DAYS = 30  # ימים קדימה
MIN_MARKET_CAP = 2000000000 # 2 מיליארד דולר מינימום (כדי לסנן זבל)

# רשימת טיקרים בסיסית (אפשר להרחיב או להשתמש בפונקציות הקודמות שלך לשאיבת NASDAQ)
# לצורך הדגמה יציבה, הסקריפט הזה ימשוך נתונים למניות ספציפיות + S&P 500
# (בגרסה המלאה שלך תשתמש בלוגיקה של NASDAQ API אם תרצה, אבל YFinance נותן את הנתונים הכספיים הכי טובים)

def get_financial_data(ticker_symbol):
    try:
        stock = yf.Ticker(ticker_symbol)
        info = stock.info
        
        # אם אין נתונים בסיסיים, דלג
        if not info or 'marketCap' not in info:
            return None

        # שליפת נתונים (The Big Three + Ratios)
        data = {
            "symbol": ticker_symbol,
            "name": info.get('shortName', ticker_symbol),
            "sector": info.get('sector', 'Unknown'),
            "marketCap": info.get('marketCap', 0),
            "earningsDate": "TBD", # נעדכן למטה
            "time": "TBD",
            
            # --- Income Statement ---
            "revenue": info.get('totalRevenue', 0),
            "revenueGrowth": info.get('revenueGrowth', 0), # YoY
            "netIncome": info.get('netIncomeToCommon', 0),
            "eps": info.get('trailingEps', 0),
            "forwardEps": info.get('forwardEps', 0), # Guidance hint
            
            # --- Balance Sheet ---
            "totalCash": info.get('totalCash', 0),
            "totalDebt": info.get('totalDebt', 0),
            "currentRatio": info.get('currentRatio', 0),
            
            # --- Cash Flow ---
            "operatingCashflow": info.get('operatingCashflow', 0),
            "freeCashflow": info.get('freeCashflow', 0),
            
            # --- Margins & Ratios ---
            "grossMargins": info.get('grossMargins', 0),
            "operatingMargins": info.get('operatingMargins', 0),
            "returnOnEquity": info.get('returnOnEquity', 0), # ROE
            "trailingPE": info.get('trailingPE', 0),
            "forwardPE": info.get('forwardPE', 0),
            
            # --- Extras ---
            "dividendYield": info.get('dividendYield', 0),
            "description": info.get('longBusinessSummary', "No description available.")
        }

        # ניסיון לחילוץ תאריך דוח הבא
        try:
            # Calendar property is often a dict or dataframe
            cal = stock.calendar
            if cal is not None:
                # לפעמים זה מגיע כמילון ולפעמים כ-DataFrame
                if isinstance(cal, dict):
                    earnings_date = cal.get('Earnings Date', [None])[0]
                else:
                    # טיפול בגרסאות חדשות של yfinance
                    earnings_date = stock.earnings_dates.index[0] # הכי קרוב
                
                if earnings_date:
                    data['earningsDate'] = str(earnings_date).split(' ')[0]
        except:
            # Fallback: אם לא הצלחנו למצוא תאריך מדויק
            pass

        return data

    except Exception as e:
        # print(f"Error fetching {ticker_symbol}: {e}")
        return None

def main():
    print("מתחיל איסוף נתונים פיננסיים עמוקים...")
    
    # רשימה לדוגמה (בפועל תשתמש ברשימת ה-S&P 500 המלאה או מה-API של NASDAQ כמו שעשינו קודם)
    # כאן אני שם רשימה מייצגת לבדיקה מהירה
    tickers = ["AAPL", "MSFT", "NVDA", "GOOG", "AMZN", "TSLA", "META", "AMD", "NFLX", "INTC", "PLTR", "SOFI", "NNE", "TSM"]
    
    final_data = []
    
    for i, sym in enumerate(tickers):
        print(f"\r מעבד: {sym} ({i+1}/{len(tickers)})...", end="")
        stock_data = get_financial_data(sym)
        if stock_data:
            # סינון דמה: נניח שהתאריך הוא בעתיד הקרוב (כי yfinance לפעמים מחזיר עבר)
            # לצורך הדוגמה באתר, נשתמש בנתונים שמצאנו
            final_data.append(stock_data)
    
    print("\n")
    
    # שמירה
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(final_data, f, ensure_ascii=False, indent=4)

    print(f"בוצע! נשמרו {len(final_data)} מניות עם דוחות כספיים מלאים.")

if __name__ == "__main__":
    main()
