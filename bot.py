import pandas as pd
import numpy as np
import time
import requests
from tqdm import tqdm
import warnings
warnings.filterwarnings('ignore')

# --- KRİPTO AYARLARI ---
TARAMA_YAPILACAK_PERIYOTLAR = {
    "30 Dakikalık": True,
    "1 Saatlik": True,
    "4 Saatlik": True,
    "Günlük": True,
}

CCI_PERIYOT = 20  
EMA_TREND = 20    
RSI_PERIYOT = 14  # RSI periyodu

# --- FİLTRE AKTİFLİK AYARLARI ---
HACIM_FILTRESI_AKTIF = True        
HACIM_ORT_PERIYOT = 10
TREND_FILTRESI_AKTIF = True        
RSI_70_ARALIK_FILTRESI_AKTIF = True    # 🚀 RSI 70-72 Aralığı (Yeni Kesişim) Filtresi Aktif
GUCLU_DONUS_FILTRESI_AKTIF = True      # Güçlü Dönüş (Dip Tepkisi / Mum Formasyonu) Filtresi

# Telegram Bildirim Ayarları
TELEGRAM_AKTIF = True
TELEGRAM_BOT_TOKEN = "8555013735:AAF_kuUHuqqrf7kD_GhXQ2s27CCM2HsXc0M"
TELEGRAM_CHAT_ID = "889982961"

def telegram_mesaj_gonder(mesaj):
    if not TELEGRAM_AKTIF:
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mesaj, "parse_mode": "Markdown", "disable_web_page_preview": True}
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"Telegram mesajı gönderilemedi: {e}")

PERIYOT_AYARLARI = {
    "30 Dakikalık": {"interval": "30m", "limit": 100},
    "1 Saatlik":    {"interval": "1h",  "limit": 100},
    "4 Saatlik":    {"interval": "4h",  "limit": 100},
    "Günlük":       {"interval": "1d",  "limit": 100}
}

# Parite Çekme Fonksiyonu
def binance_aktif_usdt_listesini_getir():
    urls = [
        "https://api.binance.com/api/v3/exchangeInfo",
        "https://data-api.binance.vision/api/v3/exchangeInfo",
        "https://api1.binance.com/api/v3/exchangeInfo"
    ]
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    for url in urls:
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                symbols = [s['symbol'] for s in data['symbols'] if s['quoteAsset'] == 'USDT' and s['status'] == 'TRADING']
                if symbols:
                    return symbols
        except Exception:
            continue
    return []

tickers = binance_aktif_usdt_listesini_getir()
print(f"✅ Binance'ten toplam {len(tickers)} adet aktif USDT paritesi çekildi.")

# 🚀 Yedekli ve İstek Sınırı Korumalı Mum Çekme Fonksiyonu
def binance_klines_cek(symbol, interval, limit=100):
    urls = [
        "https://api.binance.com/api/v3/klines",
        "https://data-api.binance.vision/api/v3/klines",
        "https://api1.binance.com/api/v3/klines"
    ]
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    for url in urls:
        try:
            response = requests.get(url, params=params, headers=headers, timeout=4)
            if response.status_code == 200:
                data = response.json()
                if not data or len(data) < max(CCI_PERIYOT + 5, RSI_PERIYOT + 5, 25):
                    return None
                df = pd.DataFrame(data, columns=[
                    'Open_time', 'Open', 'High', 'Low', 'Close', 'Volume',
                    'Close_time', 'Quote_asset_volume', 'Number_of_trades',
                    'Taker_buy_base_asset', 'Taker_buy_quote_asset', 'Ignore'
                ])
                df = df[['Open_time', 'Open', 'High', 'Low', 'Close', 'Volume']].copy()
                df[['Open', 'High', 'Low', 'Close', 'Volume']] = df[['Open', 'High', 'Low', 'Close', 'Volume']].astype(float)
                df['Timestamp'] = pd.to_datetime(df['Open_time'], unit='ms')
                df.set_index('Timestamp', inplace=True)
                return df
        except Exception:
            continue
    return None

results = []

for periyot_adi, aktif_mi in TARAMA_YAPILACAK_PERIYOTLAR.items():
    if not aktif_mi:
        continue

    print(f"\n🔍 '{periyot_adi}' periyodu için tarama başlatılıyor...")
    basarili_sayisi = 0

    for ticker in tqdm(tickers, desc=f"{periyot_adi} Taranıyor"):
        df = binance_klines_cek(ticker, PERIYOT_AYARLARI[periyot_adi]["interval"], PERIYOT_AYARLARI[periyot_adi]["limit"])
        time.sleep(0.04) 

        if df is None or df.empty:
            continue
        
        basarili_sayisi += 1

        try:
            curr_vol = float(df['Volume'].iloc[-1])
            if curr_vol == 0:
                continue

            ema20 = df['Close'].ewm(span=EMA_TREND, adjust=False).mean()
            close_curr = float(df['Close'].iloc[-1])
            ema20_curr = float(ema20.iloc[-1])

            # CCI Hesabı
            tp = (df['High'] + df['Low'] + df['Close']) / 3
            sma_tp = tp.rolling(window=CCI_PERIYOT).mean()
            mad = tp.rolling(window=CCI_PERIYOT).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
            mad_safe = np.where(mad == 0, 0.0001, mad)
            cci = (tp - sma_tp) / (0.015 * mad_safe)

            curr_cci = float(cci.iloc[-1])
            prev_cci = float(cci.iloc[-2])

            # RSI Hesabı (14 Periyot)
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=RSI_PERIYOT).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=RSI_PERIYOT).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            curr_rsi = float(rsi.iloc[-1])
            prev_rsi = float(rsi.iloc[-2])

            # 1. CCI Koşulu
            cci_kosulu = (curr_cci > -100) and (curr_cci > prev_cci)
            if not cci_kosulu:
                continue

            # 2. Trend Filtresi Koşulu
            if TREND_FILTRESI_AKTIF and close_curr < ema20_curr:
                continue  

            # 3. Hacim Filtresi Koşulu
            if HACIM_FILTRESI_AKTIF:
                vol_sma = df['Volume'].rolling(window=HACIM_ORT_PERIYOT).mean()
                if curr_vol <= float(vol_sma.iloc[-1]):
                    continue  

            # 4. 🚀 RSI 70-72 Aralığı Kesişim Koşulu (Önceki <= 70, Şimdiki 70 ile 72 arasında)
            if RSI_70_ARALIK_FILTRESI_AKTIF:
                if not (prev_rsi <= 70 and 70 < curr_rsi <= 72):
                    continue

            # 5. Güçlü Dönüş (Reversal) Koşulu
            if GUCLU_DONUS_FILTRESI_AKTIF:
                o_curr = float(df['Open'].iloc[-1])
                h_curr = float(df['High'].iloc[-1])
                l_curr = float(df['Low'].iloc[-1])
                c_curr = float(df['Close'].iloc[-1])
                
                body_size = abs(c_curr - o_curr)
                total_range = h_curr - l_curr
                
                if total_range == 0:
                    continue
                
                lower_shadow = min(o_curr, c_curr) - l_curr
                alt_fitil_orani = lower_shadow / total_range
                yesil_mum = c_curr > o_curr
                
                guclu_donus_isareti = yesil_mum and (alt_fitil_orani >= 0.25 or (body_size / total_range) >= 0.4)
                if not guclu_donus_isareti:
                    continue

            # Linkler
            tv_link = f"https://www.tradingview.com/chart/?symbol=BINANCE:{ticker}.P"
            binance_futures_link = f"https://www.binance.com/en/futures/{ticker}"

            bilgi = {
                'Zaman Dilimi': periyot_adi,
                'Coin': ticker,
                'Son Kapanis': round(close_curr, 4),
                'EMA 20': round(ema20_curr, 4),
                'Son CCI': round(curr_cci, 2),
                'Son RSI': round(curr_rsi, 2),
                'Binance Link': binance_futures_link,
                'Tarih/Saat': str(df.index[-1])
            }
            results.append(bilgi)

            msg = (
                f"🚀 *RSI 70-72 YENİ KESİŞİM SİNYALİ*\n"
                f"*Coin:* `{ticker}`\n"
                f"*Periyot:* {periyot_adi}\n"
                f"*Fiyat:* {close_curr}\n"
                f"*CCI:* {curr_cci:.2f}\n"
                f"*RSI (14):* {curr_rsi:.2f} (Önceki: {prev_rsi:.2f} -> 70-72 Aralığında!)\n"
                f"✨ *Formasyon:* Güçlü Dönüş Mumu Onaylandı\n\n"
                f"🔗 [Binance Futures İşlem Aç]({binance_futures_link})\n"
                f"📈 [{ticker} Vadeli Grafiğini Aç]({tv_link})"
            )
            telegram_mesaj_gonder(msg)

        except Exception as e:
            pass

    print(f"\nℹ️ Başarıyla taranan geçerli coin sayısı: {basarili_sayisi}")

if results:
    df_results = pd.DataFrame(results)
    df_results = df_results.sort_values(by=['Zaman Dilimi', 'Coin']).reset_index(drop=True)
    df_results.to_excel("Binance_RSI70_72_Sonuclari.xlsx", index=False)
    print(f"\n✅ Toplam {len(results)} coin tüm filtrelere ulaştı ve Excel'e kaydedildi.")
else:
    print("\n⚠️ Filtrelere uyan kripto para bulunamadı.")
