import time
import os
import json
import warnings
import numpy as np
import pandas as pd
import requests
from tqdm import tqdm

warnings.filterwarnings('ignore')

# --- SİNYAL TAKİP DOSYASI AYARI (GitHub Actions State Koruması) ---
STATE_FILE = "kripto_gonderilen_sinyaller.json"

def sinyalleri_yukle():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                bugun = time.strftime('%Y-%m-%d')
                if data.get("_tarih") != bugun:
                    return {"_tarih": bugun}
                return data
        except Exception:
            return {"_tarih": time.strftime('%Y-%m-%d')}
    return {"_tarih": time.strftime('%Y-%m-%d')}

def sinyalleri_kaydet(state):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Durum dosyası kaydedilemedi: {e}")

# --- KRİPTO AYARLARI ---
TARAMA_YAPILACAK_PERIYOTLAR = {
    "15 Dakikalık": True,
    "30 Dakikalık": True,
    "1 Saatlik":    False,
    "4 Saatlik":    False,
    "Günlük":       False,
}

EMA_HIZLI = 5
EMA_YAVAS = 8
EMA_TREND = 20      
RSI_PERIYOT = 14  
ADX_PERIYOT = 14   

# 🚀 HAFIZA YÜKLEMESİ (Coin + Periyot Bazlı Günlük Kısıtlama)
gonderilenler = sinyalleri_yukle()

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
        time.sleep(0.3)
    except Exception as e:
        print(f"Telegram mesajı gönderilemedi: {e}")

PERIYOT_AYARLARI = {
    "15 Dakikalık": {"interval": "15m", "limit": 120},
    "30 Dakikalık": {"interval": "30m", "limit": 120},
    "1 Saatlik":    {"interval": "1h",  "limit": 120},
    "4 Saatlik":    {"interval": "4h",  "limit": 120},
    "Günlük":       {"interval": "1d",  "limit": 120}
}

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

def binance_klines_cek(symbol, interval, limit=120):
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
                min_gerekli = max(EMA_TREND + 5, RSI_PERIYOT + 5, ADX_PERIYOT * 2 + 5, 30)
                if not data or len(data) < min_gerekli:
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
            close_curr = float(df['Close'].iloc[-1])

            # 1. EMA 5 ve EMA 8 Kesişim Koşulu
            ema5 = df['Close'].ewm(span=EMA_HIZLI, adjust=False).mean()
            ema8 = df['Close'].ewm(span=EMA_YAVAS, adjust=False).mean()
            
            curr_ema5 = float(ema5.iloc[-1])
            prev_ema5 = float(ema5.iloc[-2])
            curr_ema8 = float(ema8.iloc[-1])
            prev_ema8 = float(ema8.iloc[-2])

            ema_kesisim = (prev_ema5 <= prev_ema8) and (curr_ema5 > curr_ema8)
            if not ema_kesisim:
                continue

            # 2. Fiyat > EMA 20 Koşulu
            ema20 = df['Close'].ewm(span=EMA_TREND, adjust=False).mean()
            curr_ema20 = float(ema20.iloc[-1])
            if close_curr <= curr_ema20:
                continue

            # 3. RSI 48 Üstü ve Yukarı Yönlü Koşulu
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=RSI_PERIYOT).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=RSI_PERIYOT).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            curr_rsi = float(rsi.iloc[-1])
            prev_rsi = float(rsi.iloc[-2])

            rsi_kosulu = (curr_rsi > 48) and (curr_rsi > prev_rsi)
            if not rsi_kosulu:
                continue

            # 4. ADX / (+DI / -DI) Yukarı Kesişim Koşulu
            high = df['High']
            low = df['Low']
            close = df['Close']
            
            plus_dm = high.diff()
            minus_dm = low.diff()
            plus_dm = np.where((plus_dm > minus_dm) & (plus_dm > 0), plus_dm, 0.0)
            minus_dm = np.where((minus_dm > plus_dm) & (minus_dm > 0), minus_dm, 0.0)
            
            tr1 = high - low
            tr2 = np.abs(high - close.shift(1))
            tr3 = np.abs(low - close.shift(1))
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            
            atr = tr.ewm(alpha=1/ADX_PERIYOT, adjust=False).mean()
            plus_di = 100 * pd.Series(plus_dm, index=df.index).ewm(alpha=1/ADX_PERIYOT, adjust=False).mean() / atr
            minus_di = 100 * pd.Series(minus_dm, index=df.index).ewm(alpha=1/ADX_PERIYOT, adjust=False).mean() / atr
            
            curr_plus_di = float(plus_di.iloc[-1])
            prev_plus_di = float(plus_di.iloc[-2])
            curr_minus_di = float(minus_di.iloc[-1])
            prev_minus_di = float(minus_di.iloc[-2])

            adx_kesisim = (prev_plus_di <= prev_minus_di) and (curr_plus_di > curr_minus_di)
            if not adx_kesisim:
                continue

            # 5. OBV (On-Balance Volume) Yukarı Yönlü Koşulu
            obv = (np.sign(df['Close'].diff()) * df['Volume']).fillna(0).cumsum()
            curr_obv = float(obv.iloc[-1])
            prev_obv = float(obv.iloc[-2])

            obv_kosulu = curr_obv > prev_obv
            if not obv_kosulu:
                continue

            # 🚀 6. TEKRARLI BİLDİRİMİ ENGELLEME (Coin + Periyot Bazlı Günlük Kısıtlama)
            sinyal_kimligi = f"{ticker}_{periyot_adi}_EMA_RSI_ADX_OBV"

            if sinyal_kimligi in gonderilenler:
                continue  

            gonderilenler[sinyal_kimligi] = True

            # Linkler
            tv_link = f"https://www.tradingview.com/chart/?symbol=BINANCE:{ticker}.P"
            binance_futures_link = f"https://www.binance.com/en/futures/{ticker}"

            bilgi = {
                'Zaman Dilimi': periyot_adi,
                'Coin': ticker,
                'Son Kapanis': round(close_curr, 4),
                'EMA 5': round(curr_ema5, 4),
                'EMA 8': round(curr_ema8, 4),
                'EMA 20': round(curr_ema20, 4),
                'Son RSI': round(curr_rsi, 2),
                'Son +DI': round(curr_plus_di, 2),
                'Son -DI': round(curr_minus_di, 2),
                'Son OBV': round(curr_obv, 2),
                'Binance Link': binance_futures_link,
                'Tarih/Saat': str(df.index[-1])
            }
            results.append(bilgi)

            msg = (
                f"🚀 *KATI KURALLI YENİ STRATEJİ SİNYALİ*\n"
                f"*Coin:* `{ticker}`\n"
                f"*Periyot:* {periyot_adi}\n"
                f"*Fiyat:* {close_curr}\n"
                f"📈 *EMA 5 ({curr_ema5:.2f}) > EMA 8 ({curr_ema8:.2f}) Kesti*\n"
                f"📊 *Fiyat EMA 20 Üstünde ({curr_ema20:.2f})*\n"
                f"*RSI (14):* {curr_rsi:.2f} (>48 ve Yön Yukarı)\n"
                f"*+DI / -DI Kesişimi:* `+DI ({curr_plus_di:.2f}) > -DI ({curr_minus_di:.2f})`\n"
                f"📊 *OBV:* Yön Yukarı (`{curr_obv:.0f}` > `{prev_obv:.0f}`)\n\n"
                f"🔗 [Binance Futures İşlem Aç]({binance_futures_link})\n"
                f"📈 [{ticker} Vadeli Grafiğini Aç]({tv_link})"
            )
            telegram_mesaj_gonder(msg)

        except Exception:
            pass

    print(f"\nℹ️ Başarıyla taranan geçerli coin sayısı: {basarili_sayisi}")

# Takip dosyasını GitHub repoda saklanmak üzere güncelle
sinyalleri_kaydet(gonderilenler)

if results:
    df_results = pd.DataFrame(results)
    df_results = df_results.sort_values(by=['Zaman Dilimi', 'Coin']).reset_index(drop=True)
    df_results.to_excel("Binance_Katı_Kuralli_Sonuclar.xlsx", index=False)
    print(f"\n✅ Toplam {len(results)} yeni sinyal bulundu ve Excel'e kaydedildi.")
else:
    print("\n⚠️ Bu taramada yeni (daha önce gönderilmemiş) sinyal bulunamadı.")
