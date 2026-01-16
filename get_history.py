import yfinance as yf
import json
import time
import os
import random
import requests
import pandas as pd

# קבצים
SOURCE_FILE = 'data.json'
OUTPUT_FILE = 'history_data.json'

# הגדרת דפדפן מזויף כדי למנוע חסימות
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def create_session():
    """יוצר חיבור מותאם אישית לעקיפת חסימות"""
    session = requests.Session()
    session.headers.update(HEADERS)
    return session

def get_quarterly_history(symbol, session):
    """שואב נתונים רבעוניים עם ניסיון חוזר במקרה של כישלון"""
    try:
        # שימוש ב-Ticker עם ה-Session המותאם
        stock = yf.Ticker(symbol, session=session)
        
        # משיכת דוחות (פעולה כבדה)
        try:
            inc = stock.quarterly_financials
            bal = stock.quarterly_balance_sheet
            cf = stock.quarterly_cashflow
        except Exception:
            # לפעמים יאהו נכשל בפעם הראשונה, ננסה שוב אחרי שניה
            time.sleep(2)
            inc = stock.quarterly_financials
            bal = stock.quarterly_balance_sheet
            cf = stock.quarterly_cashflow

        # אם עדיין אין נתונים, דלג
        if inc is None or inc.empty: 
            return None

        history = []
        
        # לוקחים עד 8 רבעונים אחרונים (שנתיים)
        dates = inc.columns[:8]
        
        for date in dates:
            try:
                date_str = date.strftime('%Y-%m-%d')
                
                # --- חילוץ נתונים בטוח (עם בדיקה שהשורה קיימת) ---
                revenue = 0
                if 'Total Revenue' in inc.index: revenue = int(inc.loc['Total Revenue', date])
                elif 'Revenue' in inc.index: revenue = int(inc.loc['Revenue', date]) # לפעמים השם משתנה
                
                net_income = 0
                if 'Net Income' in inc.index: net_income = int(inc.loc['Net Income', date])
                
                # שולי רווח
                gross_margin = 0
                if 'Gross Profit' in inc.index and revenue > 0:
                    gp = inc.loc['Gross Profit', date]
                    gross_margin = round((gp / revenue) * 100, 2)
                
                # תזרים מזומנים חופשי (FCF)
                fcf = 0
                if not cf.empty and date in cf.columns:
                    oc = cf.loc['Operating Cash Flow', date] if 'Operating Cash Flow' in cf.index else 0
                    # Capex הוא לרוב שלילי, לכן מחברים אותו
                    capex = cf.loc['Capital Expenditure', date] if 'Capital Expenditure' in cf.index else 0
                    fcf = int(oc + capex)

                history.append({
                    "date": date_str,
                    "revenue": revenue,
                    "netIncome": net_income,
                    "grossMargin": gross_margin,
                    "freeCashFlow": fcf
                })
            except Exception as inner_e:
                continue # דלג על רבעון ספציפי אם הוא פגום

        # חישוב צמיחה שנתית (YoY) מהרבעון האחרון
        yoy_growth = 0
        if len(history) >= 5:
            last = history[0]['revenue']
            prev = history[4]['revenue'] # הרבעון המקביל לפני שנה
            if prev > 0:
                yoy_growth = round(((last - prev) / prev) * 100, 2)

        return {
            "symbol": symbol,
            "yoyRevenueGrowth": yoy_growth,
            "quarterlyHistory": history
        }

    except Exception as e:
        # print(f"Error processing {symbol}: {e}")
        return None

def main():
    print("--- מתחיל משיכת היסטוריה רבעונית (מצב בטוח) ---")
    print("התהליך יהיה איטי יותר כדי למנוע חסימות של Yahoo Finance.")
    
    if not os.path.exists(SOURCE_FILE):
        print(f"קובץ {SOURCE_FILE} חסר. הרץ קודם את get_data.py")
        return

    with open(SOURCE_FILE, 'r', encoding='utf-8') as f:
        stocks = json.load(f)
    
    # סינון: רק מניות (ETFs כמו VTI לא מדווחים רבעונית באותו אופן)
    target_stocks = [s['symbol'] for s in stocks if s.get('sector') != 'ETF']
    
    # אפשרות לדיבוג: הסר את ההערה הבאה כדי לבדוק רק על 10 מניות ראשונות
    # target_stocks = target_stocks[:10] 
    
    print(f"נמצאו {len(target_stocks)} מניות מתאימות לעיבוד.")

    full_history = {}
    my_session = create_session()
    
    start_time = time.time()
    
    for i, symbol in enumerate(target_stocks):
        print(f"\r[{i+1}/{len(target_stocks)}] עובד על: {symbol:<5}", end="")
        
        data = get_quarterly_history(symbol, my_session)
        if data:
            full_history[symbol] = data
        
        # --- ההגנה החשובה ביותר: השהיה ---
        # ממתין בין 0.5 ל-1.5 שניות בין כל מניה
        time.sleep(random.uniform(0.5, 1.5))
            
    print(f"\n\nסיום! עובדו בהצלחה {len(full_history)} מתוך {len(target_stocks)} מניות.")
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(full_history, f, ensure_ascii=False, indent=4)
    print(f"הנתונים נשמרו בקובץ: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
