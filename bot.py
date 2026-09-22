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
    '30m':  True,   # 30 Dakikalık
    '1h':  False,   # 1 Saatlik
    '4h':  False,   # 4 Saatlik
    '1d':  False    # Günlük
}

MAX_WORKERS = 15
CCI_PERIYOT = 20  # Standart CCI periyodu

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
        res = requests.get(url, headers=HEADERS, timeout=4)
        if res.status_code == 200:
            for s in res.json().get('symbols', []):
                if s['quoteAsset'] == 'USDT' and s['contractType'] == 'PERPETUAL' and s['status'] == 'TRADING':
                    all_symbols.add(s['symbol'])
    except:
        pass

    # 2. Bybit Linear API
    try:
        url = "https://api.bybit.com/v5/market/instruments-info?category=linear"
        res = requests.get(url, headers=HEADERS, timeout=4)
        if res.status_code == 200:
            for item in res.json().get('result', {}).get('list', []):
                sym = item.get('symbol', '')
                if sym.endswith('USDT'):
                    all_symbols.add(sym)
    except:
        pass

    # 3. Genişletilmiş Yedek Liste
    fallback_list = [
        "ZSUSDT", "TEAMUSDT", "BYDUSDT", "COLLECTUSDT", "CYSUSDT", "STARUSDT", "AINUSDT", "HEMIUSDT", "CLOUSDT", "BTRUSDT",
        "ESPORTSUSDT", "ONUSDT", "VELVETUSDT", "MAGMAUSDT", "CAPUSDT", "FLNCUSDT", "TACUSDT", "SKDDUSDT", "BEATUSDT", "BILLUSDT",
        "PLAYUSDT", "ZHIPUUSDT", "HANAUSDT", "SOXSUSDT", "STGUSDT", "MITOUSDT", "PRLUSDT", "SKRUSDT", "TUTUSDT", "ROBOUSDT",
        "APRUSDT", "RVNUSDT", "LABUSDT", "RAVEUSDT", "IDOLUSDT", "ZKCUSDT", "DDOSUSDT", "SIRENUSDT", "TOWNSUSDT", "WENUSDT",
        "TRIAUSDT", "CRDOUSDT", "XPINUSDT", "SQDUSDT", "ADBEUSDT", "PROMPTUSDT", "AIOUSDT", "SPORTFUNUSDT", "MINIMAXUSDT", "STABLEUSDT",
        "JCTUSDT", "ZEREBROUSDT", "NVOUSDT", "TAUSDT", "BXUSDT", "UUNITREEUSDT", "XNYUSDT", "RIVERUSDT", "BLESSUSDT", "HYUNDAIUSDT",
        "KUAISHOUUSDT", "JASMYUSDT", "SQQQUSDT", "AIAUSDT", "TRUMPUSDT", "SPXUSDT", "DKNGUSDT", "HDUSDT", "NFLXUSDT", "ICNTUSDT",
        "NAVERUSDT", "KGENUSDT", "URNMUSDT", "GWEIUSDT", "BLUAIUSDT", "CRMUSDT", "BSPUSDT", "INXUSDT", "PROMUSDT", "CVXUSDT",
        "FOGOUSDT", "YBUSDT", "GSUSDT", "SHOPUSDT", "NOWUSDT", "DEXEUSDT", "SKYAIUSDT", "MEITUANUSDT", "LUMIAUSDT", "UBERUSDT",
        "OPNUSDT", "DJTUSDT", "XANUSDT", "ZMUSDT", "SAPIENUSDT", "HUSDT", "GUAUSDT", "RREUSDT", "PDDUSDT", "TTWOUSDT",
        "BANANAS31USDT", "USARUSDT", "SOFIUSDT", "ZORAUSDT", "RECALLUSDT", "COSTUSDT", "LGELECTRONICSUSDT", "GDXUSDT", "2ZUSDT", "BICOUSDT",
        "PUMPBTCUSDT", "XPDUSDT", "SONYUSDT", "RIVNUSDT", "COOKIEUSDT", "CCUSDT", "BTCDOMUSDT", "CIENUSDT", "AGTUSDT", "BBUSDT",
        "UVXYUSDT", "ONDSUSDT", "SSLXUSDT", "DISUSDT", "PANWUSDT", "CCXMTUSDT", "BANUSDT", "PUMPUSDT", "IWMUSDT", "TENCENTUSDT",
        "VRTUSDT", "DODOXUSDT", "VUSDT", "HK0700USDT", "PAXGUSDT", "XAUUSDT", "BASUSDT", "XBIUSDT", "AVGOUSDT", "XAUTUSDT",
        "XXLEUSDT", "OOUSDT", "OGUSDT", "SCRUSDT", "MONUSDT", "BANKUSDT", "PLTRUSDT", "HIMSUSDT", "USUSDT", "TMFUSDT",
        "KOUSDT", "ZBTUSDT", "FRAXUSDT", "SOONUSDT", "MSFTUSDT", "JPMUSDT", "SANTOSUSDT", "IBMUSDT", "BASEDUSDT", "XAGUSDT",
        "BABYUSDT", "POPMARTUSDT", "PENGUUSDT", "CRCLUSDT", "WDCUSDT", "AMZNUSDT", "HK1810USDT", "WLFIUSDT", "ORCLUSDT", "PYPLUSDT",
        "BRKBUSDT", "BMTUSDT", "USDCUSDT", "ASRUSDT", "DIAUSDT", "BSBUSDT", "LLYUSDT", "KITEUSDT", "LRCXUSDT", "XPTUSDT",
        "CSCOUSDT", "GUNUSDT", "EDENUSDT", "TSTUSDT", "GIGGLEUSDT", "ALPINEUSDT", "ARIAUSDT", "SPYUSDT", "CRWVUSDT", "HMSTRUSDT",
        "FLEXUSDT", "ASMLUSDT", "ACUUSDT", "HOLOUSDT", "COPPERUSDT", "STOUSDT", "AMATUSDT", "MANTRAUSDT", "AWEUSDT", "BABAUSDT",
        "TURTLEUSDT", "MELANIAUSDT", "MRKUSDT", "TBTUSDT", "KSTRUSDT", "SNOWUSDT", "NATGASUSDT", "STRCUSDT", "TSLAUSDT", "FOLKSUSDT",
        "EWJUSDT", "SAMSUNGEMUSDT", "VSTUSDT", "SXTUSDT", "AAOIUSDT", "BARDUSDT", "NNIULAIUSDT", "WMTUSDT", "CATUSDT", "IONQUSDT",
        "TAKEUSDT", "YFIUSDT", "QNTXUSDT", "PLUMEUSDT", "SWARMSUSDT", "0GUSDT", "NVDAUSDT", "VIRTUALUSDT", "ACEUSDT", "INUSDT",
        "KATUSDT", "QQQUSDT", "TOSHIUSDT", "ONGUSDT", "TRXUSDT", "SPACEUSDT", "TXNUSDT", "JELLYJELLYUSDT", "MMTUSDT", "DOLOUSDT",
        "QUSDT", "11000RATSUSDT", "PARTIUSDT", "ACTUSDT", "POPCATUSDT", "NMRUSDT", "STBLUSDT", "EWYUSDT", "XAIUSDT", "ASTSUSDT",
        "RESOLVUSDT", "EBAYUSDT", "GRAMUSDT", "LITEUSDT", "GOOGLUSDT", "SUNUSDT", "BBXUSDT", "KLACUSDT", "GIGADEVUSDT", "GEVUSDT",
        "EDUUSDT", "BZUSDT", "UAIUSDT", "STXXUSDT", "EWZUSDT", "NOTUSDT", "MORPHOUSDT", "ASTERUSDT", "CLANKERUSDT", "TNSRUSDT",
        "BIANRENSHENGUSDT", "APPUSDT", "XVSUSDT", "ALICEUSDT", "RAREUSDT", "FIGHTUSDT", "CLUSDT", "SKYUSDT", "SPCXUSDT", "FHEUSDT",
        "TRUTHUSDT", "TLMUSDT", "APEUSDT", "GMXUSDT", "BANANAUSDT", "CYBERUSDT", "BNTUSDT", "KKODEX200USDT", "TSMUSDT", "AAPLUSDT",
        "FLUIDUSDT", "LIGHTUSDT", "RDDTUSDT", "EWTUSDT", "BELUSDT", "GTCUSDT", "SMHUSDT", "KORUUSDT", "TAGUSDT", "CRVUSDT",
        "ONTUSDT", "GLWUSDT", "EULUSDT", "OGNUSDT", "BROCCOLIF3BUSDT", "BIOUSDT", "OPENUSDT", "SAMSUNGUSDT", "NOKUSDT", "ZESTUSDT",
        "AUCTIONUSDT", "COINUSDT", "MAVUSDT", "WETUSDT", "CRWDUSDT", "TZAUSDT", "ZKPUSDT", "DRAMUSDT", "TERUSDT", "AIGENSYNUSDT",
        "ANTHROPICUSDT", "MAGICUSDT", "BCHUSDT", "FARTCOINUSDT", "RKLBUSDT", "PIPPINUSDT", "SLPUSDT", "LYTEUSDT", "MUUSDT", "TRUSTUSDT",
        "1000LUNCUSDT", "LQTYUSDT", "LYNUSDT", "SANDUSDT", "UMAUSDT", "SPKUSDT", "TQQQUSDT", "C98USDT", "MOVRUSDT", "TURBOUSDT",
        "CGPTUSDT", "B2USDT", "SHAZUSDT", "BITOUSDT", "BTCUSDT", "PIXELUSDT", "SMCIUSDT", "QNTUSDT", "ALLOUSDT", "TREEUSDT",
        "1000000MOGUSDT", "EGLDUSDT", "NEIROUSDT", "HYPEUSDT", "KAIAUSDT", "ERAUSDT", "WCTUSDT", "AIXBTUSDT", "DATAIPUSDT", "ARPAUSDT",
        "NOMUSDT", "COAIUSDT", "SAHARAUSDT", "1000BONKUSDT", "XRPUSDT", "ARCUSDT", "SOPHUSDT", "HEIUSDT", "11000CHEEMSUSDT", "SKHYNIXUSDT",
        "PENGUSDT", "BOTUSDT", "NXPCUSDT", "SPELLUSDT", "USTCUSDT", "RLCUSDT", "ETHUSDT", "TRBUSDT", "1000SATSUSDT", "JSTUSDT",
        "LINEAUSDT", "NBISUSDT", "ETHWUSDT", "LAYERUSDT", "CBRSUSDT", "HAEDALUSDT", "MEWUSDT", "BBMNRUSDT", "HOMEUSDT", "HYPERUSDT",
        "BREVUSDT", "CSOPSAMSUNG2LUSDT", "IRYSUSDT", "WOOUSDT", "TWTUSDT", "QCOMUSDT", "CTKUSDT", "ATUSDT", "GPSUSDT", "SNDKUSDT",
        "SHELLUSDT", "HANMIUSDT", "XMRUSDT", "11000000BOBUSDT", "BRETTUSDT", "ENSOUSDT", "KAITOUSDT", "NETUSDT", "BIRBUSDT", "DOGSUSDT",
        "RAMUSDT", "SKHYUSDT", "FUSDT", "AEVOUSDT", "MAVIAUSDT", "MEMEUSDT", "CARVUSDT", "ALABUSDT", "ZROUSDT", "MOVEUSDT",
        "GMTUSDT", "CETUSUSDT", "MASKUSDT", "THEUSDT", "GLMUSDT", "ENJUSDT", "MYXUSDT", "SNXUSDT", "COHRUSDT", "1INCHUSDT",
        "AVNTUSDT", "ENSUSDT", "MUUUSDT", "IDUSDT", "EVAAUSDT", "SOLUSDT", "FIDAUSDT", "ARKMUSDT", "XPLUSDT", "API3USDT",
        "AAVEUSDT", "JOEUSDT", "PNUTUSDT", "NEWTUSDT", "LINKUSDT", "ATHUSDT", "HUMAUSDT", "ANIMEUSDT", "GASUSDT", "BSVUSDT",
        "BNBUSDT", "COMPUSDT", "PEOPLEUSDT", "COTIUSDT", "CFXUSDT", "MOCAUSDT", "JTOUSDT", "CHRUSDT", "GGRVTUSDT", "IOUSDT",
        "BANDUSDT", "1MBABYDOGEUSDT", "HOODUSDT", "SFPUSDT", "PAYPUSDT", "MEGAUSDT", "YGGUSDT", "HPEUSDT", "11000SHIBUSDT", "SAFEUSDT",
        "ORDERUSDT", "MIRAUSDT", "CHIPUSDT", "CTSIUSDT", "AXSUSDT", "11000FLOKIUSDT", "MANAUSDT", "BOMEUSDT", "ELSAUSDT", "BROCCOLI714USDT",
        "AALLUSDT", "GOATUSDT", "AXLUSDT", "ORCAUSDT", "QTUMUSDT", "DYMUSDT", "DOGEUSDT", "ESPUSDT", "WIFUSDT", "CHZUSDT",
        "MEUSDT", "IOTAUSDT", "USUALUSDT", "RIFUSDT", "LISTAUSDT", "MOODENGUSDT", "UBUSDT", "ETCUSDT", "IMXUSDT", "MANTAUSDT",
        "SSVUSDT", "1000XECUSDT", "CATIUSDT", "EIGENUSDT", "GALAUSDT", "CSOPSKHYNIX2LUSDT", "XVGUSDT", "LDOUSDT", "MRVLUSDT", "LAUSDT",
        "AZTECUSDT", "RONINUSDT", "XLMUSDT", "ALTUSDT", "NEOUSDT", "RSRUSDT", "TAIKOUSDT", "SONICUSDT", "ILVUSDT", "TRADOORUSDT",
        "LUNA2USDT", "GENIUSUSDT", "ATOMUSDT", "RPLUSDT", "AUSDT", "ACHUSDT", "11000CATUSDT", "SKLUSDT", "BATUSDT", "VANAUSDT",
        "POLUSDT", "MARAUSDT", "ZHONGJIUSDT", "TEMUSDT", "AGLDUSDT", "FLOWUSDT", "ADAUSDT", "ICPUSDT", "WOTAMALAILIAOUSDT", "WLDUSDT",
        "SYRUPUSDT", "FLUXUSDT", "ORDIUSDT", "CKBUSDT", "MRNAUSDT", "CCTRUSDT", "BIGTIMEUSDT", "HBARUSDT", "DELLUSDT", "KERNELUSDT",
        "SNXXUSDT", "CELOUSDT", "ASTRUSDT", "ZRXUSDT", "SOXLUSDT", "BERAUSDT", "ANKRUSDT", "ETHFIUSDT", "ROSEUSDT", "AVAUSDT",
        "BEAMXUSDT", "GRASSUSDT", "HIVEUSDT", "PYTHUSDT", "CHILLGUYUSDT", "CFGUSDT", "POLYXUSDT", "IRENUSDT", "WAXPUSDT", "SKUUUSDT",
        "GMEUSDT", "WUSDT", "DUSKUSDT", "BLURUSDT", "IOTXUSDT", "LTCUSDT", "TIAUSDT", "AIOTUSDT", "NILUSDT", "LPTUSDT",
        "COWUSDT", "MSTRUSDT", "DYDXUSDT", "SUSHIUSDT", "AKTUSDT", "METAUSDT", "KSMUSDT", "MTLUSDT", "FWDIUSDT", "AVAAIUSDT",
        "FETUSDT", "KNCUSDT", "RENDERUSDT", "ONDOUSDT", "ALGOUSDT", "DASHUSDT", "AMDUSDT", "NIGHTUSDT", "PUNDIXUSDT", "REZUSDT",
        "BEUSDT", "ZKUSDT", "AXTIUSDT", "JUPUSDT", "RUNEUSDT", "METISUSDT", "LITUSDT", "THETAUSDT", "GRIFFAINUSDT", "STEEMUSDT",
        "PROVEUSDT", "SEIUSDT", "ARMUSDT", "MERLUSDT", "OPENAIUSDT", "MUSDT", "OPUSDT", "TAOUSDT", "1000PEPEUSDT", "ZENUSDT",
        "STXUSDT", "INTCUSDT", "VETUSDT", "CAKEUSDT", "OPGUSDT", "VELODROMEUSDT", "CUSDT", "CROSSUSDT", "PORTALUSDT", "DRIFTUSDT",
        "POWRUSDT", "ZILUSDT", "INITUSDT", "SUPERUSDT", "SIGNUSDT", "KMNOUSDT", "ENAUSDT", "CVCUSDT", "ARKUSDT", "DEEPUSDT",
        "SUIUSDT", "PHAROSUSDT", "WALUSDT", "SUSDT", "GRTUSDT", "DOTUSDT", "CELRUSDT", "SOLVUSDT", "FORMUSDT", "DOODUSDT",
        "PENDLEUSDT", "MVLLUSDT", "NAORISUSDT", "METUSDT", "TUSDT", "FILUSDT", "REDUSDT", "POWERUSDT", "AEROUSDT", "APTUSDT",
        "SENTUSDT", "BUSDT", "FFUSDT", "KAVAUSDT", "IOSTUSDT", "EDGEUSDT", "SOMIUSDT", "KASUSDT", "AVAXUSDT", "AARXUSDT",
        "INJUSDT", "PTBUSDT", "XTZUSDT", "4USDT", "UNIUSDT", "VTHOUSDT", "STRKUSDT", "KOMAUSDT", "GUSDT", "ZECUSDT",
        "INTWUSDT", "PIEVERSEUSDT", "ZETAUSDT", "ZAMAUSDT", "EPICUSDT", "ALCHUSDT", "FLOCKUSDT", "MINAUSDT", "VVVUSDT", "PHAUSDT",
        "ARBUSDT", "MUBARAKUSDT", "BTWUSDT", "NEARUSDT", "BNCUSDT", "ARUSDT", "RAYSOLUSDT", "SAGAUSDT"
    ]

    for sym in fallback_list:
        all_symbols.add(sym)

    return sorted(list(all_symbols))

PERIYOT_DETAYLARI = {
    '30m': {'binance': '30m', 'okx': '30m', 'label': '30 Dakikalık'},
    '1h':  {'binance': '1h',  'okx': '1H',    'label': '1 Saatlik'},
    '4h':  {'binance': '4h',  'okx': '4H',    'label': '4 Saatlik'},
    '1d':  {'binance': '1d',  'okx': '1DUTC', 'label': 'Günlük'}
}

ENDPOINTS = [
    "https://fapi.binance.com/fapi/v1/klines",
    "https://fapi1.binance.com/fapi/v1/klines",
    "https://fapi2.binance.com/fapi/v1/klines",
    "https://fapi3.binance.com/fapi/v1/klines"
]

def get_klines(symbol, interval_info):
    for endpoint in ENDPOINTS:
        try:
            url = f"{endpoint}?symbol={symbol}&interval={interval_info['binance']}&limit=100"
            res = requests.get(url, headers=HEADERS, timeout=2.0)
            if res.status_code == 200:
                data = res.json()
                if isinstance(data, list) and len(data) > 0:
                    df = pd.DataFrame(data, columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume', 'ct', 'qv', 'tr', 'tb', 'tq', 'ig'])
                    return format_df(df)
        except:
            continue

    try:
        okx_symbol = symbol.replace("USDT", "-USDT-SWAP")
        if symbol.startswith("1000"):
            okx_symbol = symbol.replace("1000", "").replace("USDT", "-USDT-SWAP")

        url = f"https://www.okx.com/api/v5/market/candles?instId={okx_symbol}&bar={interval_info['okx']}&limit=100"
        res = requests.get(url, headers=HEADERS, timeout=2.0)
        if res.status_code == 200:
            data = res.json().get('data', [])
            if data:
                df = pd.DataFrame(data, columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume', 'vCcy', 'vCcyQuote', 'confirm'])
                df = df.iloc[::-1].reset_index(drop=True)
                return format_df(df)
    except:
        pass

    return pd.DataFrame()

def format_df(df):
    df = df[['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume']]
    for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
        df[col] = df[col].astype(float)
    df['Timestamp'] = pd.to_datetime(df['Timestamp'].astype(int), unit='ms')
    return df

def analyze_symbol(symbol, key, info, sent_signals):
    df = get_klines(symbol, info)

    if df.empty or len(df) < max(CCI_PERIYOT + 5, 30):
        return None

    candle_time = str(df['Timestamp'].iloc[-2])
    unique_key = f"{symbol}_{key}_{candle_time}"

    if unique_key in sent_signals:
        return None

    ema6 = df['Close'].ewm(span=6, adjust=False).mean()
    
    close_curr = float(df['Close'].iloc[-2])
    close_prev = float(df['Close'].iloc[-3])
    ema6_curr = float(ema6.iloc[-2])
    ema6_prev = float(ema6.iloc[-3])

    ema6_cross_above = (close_curr > ema6_curr) and (close_prev <= ema6_prev)

    if not ema6_cross_above:
        return None

    tp = (df['High'] + df['Low'] + df['Close']) / 3
    sma_tp = tp.rolling(window=CCI_PERIYOT).mean()
    mad = tp.rolling(window=CCI_PERIYOT).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
    cci = (tp - sma_tp) / (0.015 * mad)

    prev_cci = float(cci.iloc[-3])
    curr_cci = float(cci.iloc[-2])

    cci_cross_above_minus100 = (prev_cci < -100) and (curr_cci >= -100)

    if cci_cross_above_minus100:
        tv_link = f"https://www.tradingview.com/chart/?symbol=BINANCE:{symbol}"
        binance_link = f"https://www.binance.com/tr/futures/{symbol}"
        
        msg = (
            f"🚨 *KRİPTO SİNYAL YAKALANDI!*\n"
            f"*Coin:* `{symbol}`\n"
            f"*Periyot:* {info['label']}\n"
            f"*Fiyat:* {close_curr}\n"
            f"*CCI(20):* {curr_cci:.2f}\n\n"
            f"📈 [TradingView Grafiği]({tv_link})\n"
            f"🟡 [Binance Futures İşlem]({binance_link})"
        )
        telegram_mesaj_gonder(msg)
        return unique_key

    return None

if __name__ == "__main__":
    print(f"🔄 GitHub Action Taraması Başladı: {datetime.now()}")
    sent_signals = load_sent_signals()
    
    if len(sent_signals) > 300:
        sent_signals = sent_signals[-300:]

    symbols = get_master_symbol_list()
    new_signals_found = []

    for key, aktif in TARAMA_PERIYOTLARI.items():
        if not aktif:
            continue

        info = PERIYOT_DETAYLARI[key]
        print(f"⚡ {info['label']} periyodu taranıyor...")

        def worker(sym):
            return analyze_symbol(sym, key, info, sent_signals)

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            results = list(executor.map(worker, symbols))
            for res in results:
                if res:
                    new_signals_found.append(res)

    if new_signals_found:
        sent_signals.extend(new_signals_found)
        save_sent_signals(sent_signals)
        print(f"✅ {len(new_signals_found)} yeni sinyal bulundu ve kaydedildi.")
    else:
        print("ℹ️ Yeni sinyal bulunamadı.")
