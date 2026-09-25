import os
import json
import pandas as pd
import numpy as np
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import warnings
warnings.filterwarnings('ignore')

# ==========================================
# --- TARAMA VE FİLTRE AYARLARI ---
# ==========================================
TARAMA_PERIYOTLARI = {
    '30m': True,    # 30 Dakikalık
    '1h':  True,    # 1 Saatlik
    '4h':  True,    # 4 Saatlik
    '1d':  True     # Günlük
}

MAX_WORKERS = 15
CCI_PERIYOT = 20    # Standart CCI periyodu
RSI_PERIYOT = 14    # Standart RSI periyodu

# --- TELEGRAM BİLDİRİM AYARLARI ---
TELEGRAM_AKTIF = True
TELEGRAM_BOT_TOKEN = "8836424298:AAEtI7MUlrvlhhta7ydURvDPcRFck0Ps6os"
TELEGRAM_CHAT_ID = "889982961"

STATE_FILE = "sent_signals.json"

def load_sent_signals():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except:
            return []
    return []

def save_sent_signals(signals):
    with open(STATE_FILE, "w") as f:
        json.dump(signals, f, indent=4)

def telegram_mesaj_gonder(mesaj):
    if not TELEGRAM_AKTIF:
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mesaj, "parse_mode": "Markdown", "disable_web_page_preview": True}
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"Telegram mesajı gönderilemedi: {e}")
# ==========================================

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'application/json'
}

def get_master_symbol_list():
    all_symbols = set()

    # 1. Binance Futures API
    try:
        url = "https://fapi.binance.com/fapi/v1/exchangeInfo"
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            data = response.json()
            for s in data.get('symbols', []):
                if s['status'] == 'TRADING' and s['quoteAsset'] == 'USDT':
                    all_symbols.add(s['symbol'])
    except Exception as e:
        print(f"Binance Futures sembolleri alınırken hata: {e}")

    return list(all_symbols)

def get_historical_data(symbol, interval):
    url = f"https://fapi.binance.com/fapi/v1/klines"
    params = {
        'symbol': symbol,
        'interval': interval,
        'limit': 100
    }
    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=10)
        if response.status_code == 200:
            raw_data = response.json()
            if not raw_data:
                return None
            
            df = pd.DataFrame(raw_data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_vol', 'taker_buy_quote_vol', 'ignore'
            ])
            
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
                
            return df
    except Exception as e:
        print(f"{symbol} ({interval}) veri çekme hatası: {e}")
    return None

def hesapla_cci(df, period=CCI_PERIYOT):
    tp = (df['high'] + df['low'] + df['close']) / 3
    sma_tp = tp.rolling(window=period).mean()
    mad = tp.rolling(window=period).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
    cci = (tp - sma_tp) / (0.015 * mad)
    df['cci'] = cci
    return df

def hesapla_rsi(df, period=RSI_PERIYOT):
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    df['rsi'] = rsi
    return df

def analyze_symbol(symbol):
    results = []
    sent_signals = load_sent_signals()
    
    for periyot, aktif in TARAMA_PERIYOTLARI.items():
        if not aktif:
            continue
            
        df = get_historical_data(symbol, periyot)
        if df is None or len(df) < max(CCI_PERIYOT, RSI_PERIYOT) + 5:
            continue
            
        df = hesapla_cci(df, CCI_PERIYOT)
        df = hesapla_rsi(df, RSI_PERIYOT)
        
        son_cci = df['cci'].iloc[-1]
        onceki_cci = df['cci'].iloc[-2]
        
        son_rsi = df['rsi'].iloc[-1]
        onceki_rsi = df['rsi'].iloc[-2]
        
        # 1. CCI Sinyal Kontrolü (Örn: +100 yukarı kesişim)
        cci_long = (onceki_cci < 100 and son_cci >= 100)
        
        # 2. RSI Sinyal Kontrolü (70'i yukarı kesmiş ve 69 - 75 aralığında yani 72 civarında)
        rsi_kesisim = (onceki_rsi < 70 and son_rsi >= 70)
        rsi_seviye = (69.0 <= son_rsi <= 75.0)
        
        yon = None
        # Hem CCI kesişimi hem de RSI şartı sağlanıyorsa LONG sinyali üret
        if cci_long and rsi_kesisim and rsi_seviye:
            yon = "LONG (CCI > +100 & RSI ~72 Kesişimi)"
            
        if yon:
            signal_id = f"{symbol}_{periyot}_{yon.split()[0]}"
            if signal_id not in sent_signals:
                mesaj = (
                    f"🚨 **Güçlü Trend Sinyali (CCI + RSI)!**\n\n"
                    f"🔹 **Sembol:** `{symbol}`\n"
                    f"⏱ **Periyot:** `{periyot}`\n"
                    f"📊 **Yön:** **{yon}**\n"
                    f"📈 **Güncel CCI:** `{son_cci:.2f}`\n"
                    f"📉 **Güncel RSI:** `{son_rsi:.2f}`\n"
                    f"🕒 **Zaman:** `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`"
                )
                telegram_mesaj_gonder(mesaj)
                sent_signals.append(signal_id)
                save_sent_signals(sent_signals)
                
    return results

def main():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Tarama başlatılıyor...")
    symbols = get_master_symbol_list()
    print(f"Toplam {len(symbols)} adet USDT vadeli işlem çifti taranacak.")
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        executor.map(analyze_symbol, symbols)
        
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Tarama tamamlandı.")

if __name__ == "__main__":
    main()
