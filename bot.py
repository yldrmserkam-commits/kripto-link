import yfinance as yf
import pandas as pd
import numpy as np
import time
import requests
from tqdm import tqdm
import warnings
warnings.filterwarnings('ignore')

# --- AYARLAR ---
TARAMA_YAPILACAK_PERIYOTLAR = {
    "30 Dakikalık": True,
    "1 Saatlik": True,
    "4 Saatlik": True,
    "Günlük": False,
    "Haftalık": False,
    "Aylık": False
}

CCI_PERIYOT = 20  
EMA_TREND = 20    
RSI_PERIYOT = 14  # RSI periyodu

# --- FİLTRE AKTİFLİK AYARLARI ---
HACIM_FILTRESI_AKTIF = True        
HACIM_ORT_PERIYOT = 10
TREND_FILTRESI_AKTIF = True        
CHIKOU_KIJUN_FILTRESI_AKTIF = True    
RSI_FILTRESI_AKTIF = True         # RSI Filtresi Aktif

# Telegram Bildirim Ayarları
TELEGRAM_AKTIF = True
TELEGRAM_BOT_TOKEN = "8909661577:AAExPm7d6hohqkZV9XG_FMTcjjU_Z3hP92w"
TELEGRAM_CHAT_ID = "889982961"

def telegram_mesaj_gonder(mesaj):
    if not TELEGRAM_AKTIF:
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID, 
            "text": mesaj, 
            "parse_mode": "Markdown", 
            "disable_web_page_preview": True
        }
        response = requests.post(url, json=payload, timeout=5)
        if response.status_code != 200:
            print(f"Telegram API Hatası: {response.text}")
    except Exception as e:
        print(f"Telegram mesajı gönderilemedi: {e}")

PERIYOT_AYARLARI = {
    "30 Dakikalık": {"interval": "30m", "period": "60d", "resample_rule": None},
    "1 Saatlik":    {"interval": "60m", "period": "90d", "resample_rule": None},
    "4 Saatlik":    {"interval": "60m", "period": "90d", "resample_rule": "4h"},
    "Günlük":        {"interval": "1d",  "period": "1y",  "resample_rule": None},
    "Haftalık":     {"interval": "1wk", "period": "3y",  "resample_rule": None},
    "Aylık":         {"interval": "1mo", "period": "max", "resample_rule": None}
}

ham_tickers = [
    'A1CAP.IS', 'A1YEN.IS', 'AAGYO.IS', 'ACSEL.IS', 'ADEL.IS', 'ADESE.IS', 'ADGYO.IS',
    'AEFES.IS', 'AFYON.IS', 'AGESA.IS', 'AGHOL.IS', 'AGROT.IS', 'AGYO.IS', 'AHGAZ.IS',
    'AHSGY.IS', 'AKBNK.IS', 'AKCNS.IS', 'AKENR.IS', 'AKFGY.IS', 'AKFIS.IS', 'AKFYE.IS',
    'AKGRT.IS', 'AKHAN.IS', 'AKMGY.IS', 'AKSA.IS', 'AKSEN.IS', 'AKSGY.IS', 'AKSUE.IS',
    'AKYHO.IS', 'ALARK.IS', 'ALBRK.IS', 'ALBTN.IS', 'ALCAR.IS', 'ALCTL.IS', 'ALFAS.IS',
    'ALGYO.IS', 'ALKA.IS', 'ALKIM.IS', 'ALKLC.IS', 'ALTINS1.IS', 'ALTNY.IS', 'ALVES.IS',
    'ANELE.IS', 'ANGEN.IS', 'ANHYT.IS', 'ANSGR.IS', 'ARASE.IS', 'ARCLK.IS', 'ARDYZ.IS',
    'ARENA.IS', 'ARFYE.IS', 'ARMGD.IS', 'ARSAN.IS', 'ARTMS.IS', 'ARZUM.IS', 'ASELS.IS',
    'ASGYO.IS', 'ASTOR.IS', 'ASUZU.IS', 'ATAGY.IS', 'ATAKP.IS', 'ATATP.IS', 'ATATR.IS',
    'ATEKS.IS', 'ATLAS.IS', 'ATSYH.IS', 'AVGYO.IS', 'AVHOL.IS', 'AVOD.IS', 'AVPGY.IS',
    'AVTUR.IS', 'AYCES.IS', 'AYDEM.IS', 'AYEN.IS', 'AYES.IS', 'AYGAZ.IS', 'AZTEK.IS',
    'BAGFS.IS', 'BAHKM.IS', 'BAKAB.IS', 'BALAT.IS', 'BALSU.IS', 'BANVT.IS', 'BARMA.IS',
    'BASCM.IS', 'BASGZ.IS', 'BAYRK.IS', 'BEGYO.IS', 'BERA.IS', 'BESLR.IS', 'BESTE.IS',
    'BETAE.IS', 'BEYAZ.IS', 'BFREN.IS', 'BIENY.IS', 'BIGCH.IS', 'BIGEN.IS', 'BIGTK.IS',
    'BIMAS.IS', 'BINBN.IS', 'BINHO.IS', 'BIOEN.IS', 'BIZIM.IS', 'BJKAS.IS', 'BKRGY.IS',
    'BLCYT.IS', 'BLUME.IS', 'BMSCH.IS', 'BMSTL.IS', 'BNTAS.IS', 'BOBET.IS', 'BORLS.IS',
    'BORSK.IS', 'BOSSA.IS', 'BRISA.IS', 'BRKO.IS', 'BRKSN.IS', 'BRKVY.IS', 'BRLSM.IS',
    'BRMEN.IS', 'BRSAN.IS', 'BRYAT.IS', 'BSOKE.IS', 'BTCIM.IS', 'BUCIM.IS', 'BULGS.IS',
    'BURCE.IS', 'BURVA.IS', 'BVSAN.IS', 'BYDNR.IS', 'CANTE.IS', 'CASA.IS', 'CATES.IS',
    'CCOLA.IS', 'CELHA.IS', 'CEMAS.IS', 'CEMTS.IS', 'CEMZY.IS', 'CEOEM.IS', 'CGCAM.IS',
    'CIMSA.IS', 'CITAS.IS', 'CLEBI.IS', 'CMBTN.IS', 'CMENT.IS', 'CONSE.IS', 'COSMO.IS',
    'CRDFA.IS', 'CRFSA.IS', 'CUSAN.IS', 'CVKMD.IS', 'CWENE.IS', 'DAGI.IS', 'DAPGM.IS',
    'DARDL.IS', 'DCTTR.IS', 'DENGE.IS', 'DERHL.IS', 'DERIM.IS', 'DESA.IS', 'DESPC.IS',
    'DEVA.IS', 'DGATE.IS', 'DGGYO.IS', 'DGNMO.IS', 'DIRIT.IS', 'DITAS.IS', 'DMLKTG.IS',
    'DMRGD.IS', 'DMSAS.IS', 'DNISI.IS', 'DOAS.IS', 'DOCO.IS', 'DOFER.IS', 'DOFRB.IS',
    'DOGUB.IS', 'DOHOL.IS', 'DOKTA.IS', 'DSTKF.IS', 'DUNYH.IS', 'DURDO.IS', 'DURKN.IS',
    'DYOBY.IS', 'DZGYO.IS', 'EBEBK.IS', 'ECILC.IS', 'ECOGR.IS', 'ECZYT.IS', 'EDATA.IS',
    'EDIP.IS', 'EFOR.IS', 'EGEEN.IS', 'EGEGY.IS', 'EGEPO.IS', 'EGGUB.IS', 'EGPRO.IS',
    'EGSER.IS', 'EKDMR.IS', 'EKGYO.IS', 'EKIM.IS', 'EKIZ.IS', 'EKOS.IS', 'EKSUN.IS',
    'ELITE.IS', 'EMKEL.IS', 'EMNIS.IS', 'EMPAE.IS', 'ENDAE.IS', 'ENERY.IS', 'ENJSA.IS',
    'ENKAI.IS', 'ENPRA.IS', 'ENSRI.IS', 'ENTRA.IS', 'EPLAS.IS', 'ERBOS.IS', 'ERCB.IS',
    'EREGL.IS', 'ERSU.IS', 'ESCAR.IS', 'ESCOM.IS', 'ESEN.IS', 'ETILR.IS', 'ETYAT.IS',
    'EUHOL.IS', 'EUKYO.IS', 'EUPWR.IS', 'EUREN.IS', 'EUYO.IS', 'EYGYO.IS', 'FADE.IS',
    'FENER.IS', 'FLAP.IS', 'FMIZP.IS', 'FONET.IS', 'FORMT.IS', 'FORTE.IS', 'FRIGO.IS',
    'FRMPL.IS', 'FROTO.IS', 'FZLGY.IS', 'GARAN.IS', 'GARFA.IS', 'GATEG.IS', 'GEDIK.IS',
    'GEDZA.IS', 'GENIL.IS', 'GENKM.IS', 'GENTS.IS', 'GEREL.IS', 'GESAN.IS', 'GIPTA.IS',
    'GLBMD.IS', 'GLCVY.IS', 'GLRMK.IS', 'GLRYH.IS', 'GLYHO.IS', 'GMTAS.IS', 'GOKNR.IS',
    'GOLDA.IS', 'GOLTS.IS', 'GOODY.IS', 'GOZDE.IS', 'GRNYO.IS', 'GRSEL.IS', 'GRTHO.IS',
    'GSDDE.IS', 'GSDHO.IS', 'GSRAY.IS', 'GUBRF.IS', 'GUNDG.IS', 'GWIND.IS', 'GZNMI.IS',
    'HALKB.IS', 'HATEK.IS', 'HATSN.IS', 'HDFGS.IS', 'HEDEF.IS', 'HEKTS.IS', 'HKTM.IS',
    'HLGYO.IS', 'HOROZ.IS', 'HRKET.IS', 'HTTBT.IS', 'HUBVC.IS', 'HUNER.IS', 'HURGZ.IS',
    'ICBCT.IS', 'ICUGS.IS', 'IDGYO.IS', 'IEYHO.IS', 'IHAAS.IS', 'IHEVA.IS', 'IHGZT.IS',
    'IHLAS.IS', 'IHLGM.IS', 'IHYAY.IS', 'IMASM.IS', 'INDES.IS', 'INFO.IS', 'INGRM.IS',
    'INTEK.IS', 'INTEM.IS', 'INTET.IS', 'INVEO.IS', 'INVES.IS', 'ISATR.IS', 'ISBIR.IS',
    'ISBTR.IS', 'ISCTR.IS', 'ISDMR.IS', 'ISFIN.IS', 'ISGSY.IS', 'ISGYO.IS', 'ISKPL.IS',
    'ISKUR.IS', 'ISMEN.IS', 'ISSEN.IS', 'ISVEA.IS', 'ISYAT.IS', 'IZENR.IS', 'IZFAS.IS',
    'IZINV.IS', 'IZMDC.IS', 'JANTS.IS', 'KAPLM.IS', 'KARCL.IS', 'KAREL.IS', 'KARSN.IS',
    'KARTN.IS', 'KATMR.IS', 'KAYSE.IS', 'KBORU.IS', 'KCAER.IS', 'KCHOL.IS', 'KENT.IS',
    'KERVN.IS', 'KFEIN.IS', 'KGYO.IS', 'KIMMR.IS', 'KLGYO.IS', 'KLKIM.IS', 'KLMSN.IS',
    'KLNMA.IS', 'KLRHO.IS', 'KLSER.IS', 'KLSYN.IS', 'KLYPV.IS', 'KMPUR.IS', 'KNFRT.IS',
    'KOCMT.IS', 'KONKA.IS', 'KONTR.IS', 'KONYA.IS', 'KOPOL.IS', 'KORDS.IS', 'KOTON.IS',
    'KPEKS.IS', 'KRDMA.IS', 'KRDMB.IS', 'KRDMD.IS', 'KRGYO.IS', 'KRONT.IS', 'KRPLS.IS',
    'KRSTL.IS', 'KRTEK.IS', 'KRVGD.IS', 'KSTUR.IS', 'KTLEV.IS', 'KTSKR.IS', 'KUTPO.IS',
    'KUVVA.IS', 'KUYAS.IS', 'KZBGY.IS', 'KZGYO.IS', 'LIDER.IS', 'LIDFA.IS', 'LILAK.IS',
    'LINK.IS', 'LKMNH.IS', 'LMKDC.IS', 'LOGO.IS', 'LRSHO.IS', 'LUKSK.IS', 'LXGYO.IS',
    'LYDHO.IS', 'LYDYE.IS', 'MAALT.IS', 'MACKO.IS', 'MAGEN.IS', 'MAKIM.IS', 'MAKTK.IS',
    'MANAS.IS', 'MARBL.IS', 'MARMR.IS', 'MARTI.IS', 'MASFN.IS', 'MAVI.IS', 'MCARD.IS',
    'MEDTR.IS', 'MEGAP.IS', 'MEGMT.IS', 'MEKAG.IS', 'MEPET.IS', 'MERCN.IS', 'MERIT.IS',
    'MERKO.IS', 'METEN.IS', 'METRO.IS', 'MEYSU.IS', 'MGROS.IS', 'MHRGY.IS', 'MIATK.IS',
    'MMCAS.IS', 'MNDRS.IS', 'MNDTR.IS', 'MOBTL.IS', 'MOGAN.IS', 'MOPAS.IS', 'MPARK.IS',
    'MRGYO.IS', 'MRSHL.IS', 'MSGYO.IS', 'MTRKS.IS', 'MTRYO.IS', 'MZHLD.IS', 'NATEN.IS',
    'NETAS.IS', 'NETCD.IS', 'NIBAS.IS', 'NTGAZ.IS', 'NTHOL.IS', 'NUGYO.IS', 'NUHCM.IS',
    'OBAMS.IS', 'OBASE.IS', 'ODAS.IS', 'ODINE.IS', 'OFSYM.IS', 'ONCSM.IS', 'ONRYT.IS',
    'ORCAY.IS', 'ORGE.IS', 'ORMA.IS', 'ORZAX.IS', 'OSMEN.IS', 'OSTIM.IS', 'OTKAR.IS',
    'OTTO.IS', 'OYAKC.IS', 'OYAYO.IS', 'OYLUM.IS', 'OYYAT.IS', 'OZATD.IS', 'OZGYO.IS',
    'OZKGY.IS', 'OZRDN.IS', 'OZSUB.IS', 'OZYSR.IS', 'PAGYO.IS', 'PAHOL.IS', 'PAMEL.IS',
    'PAPIL.IS', 'PARSN.IS', 'PASEU.IS', 'PATEK.IS', 'PCILT.IS', 'PEKGY.IS', 'PENGD.IS',
    'PENTA.IS', 'PETKM.IS', 'PETUN.IS', 'PGSUS.IS', 'PINSU.IS', 'PKART.IS', 'PKENT.IS',
    'PLTUR.IS', 'PNLSN.IS', 'PNSUT.IS', 'POLHO.IS', 'POLTK.IS', 'PRDGS.IS', 'PRKAB.IS',
    'PRKME.IS', 'PRZMA.IS', 'PSDTC.IS', 'PSGYO.IS', 'QNBFK.IS', 'QNBTR.IS', 'QUAGR.IS',
    'QUICK.IS', 'RALYH.IS', 'RAYSG.IS', 'REEDR.IS', 'RGYAS.IS', 'RNPOL.IS', 'RODRG.IS',
    'RTALB.IS', 'RUBNS.IS', 'RUZYE.IS', 'RYGYO.IS', 'RYSAS.IS', 'SAFKR.IS', 'SAHOL.IS',
    'SAMAT.IS', 'SANEL.IS', 'SANKO.IS', 'SARAE.IS', 'SARKY.IS', 'SASA.IS', 'SAYAS.IS',
    'SDTTR.IS', 'SEGMN.IS', 'SEGYO.IS', 'SEKFK.IS', 'SEKUR.IS', 'SELEC.IS', 'SELVA.IS',
    'SERNT.IS', 'SEYKM.IS', 'SILVR.IS', 'SISE.IS', 'SKBNK.IS', 'SKTAS.IS', 'SKYLP.IS',
    'SKYMD.IS', 'SMART.IS', 'SMRTG.IS', 'SMRVA.IS', 'SNGYO.IS', 'SNICA.IS', 'SNPAM.IS',
    'SODSN.IS', 'SOHOE.IS', 'SOKE.IS', 'SOKM.IS', 'SONME.IS', 'SRVGY.IS', 'SSAAT.IS',
    'SUMAS.IS', 'SUNTK.IS', 'SURGY.IS', 'SUWEN.IS', 'SVGYO.IS', 'TABGD.IS', 'TARKM.IS',
    'TATEN.IS', 'TATGD.IS', 'TAVHL.IS', 'TBORG.IS', 'TCELL.IS', 'TCKRC.IS', 'TDGYO.IS',
    'TEHOL.IS', 'TEKTU.IS', 'TERA.IS', 'TEZOL.IS', 'TGSAS.IS', 'THYAO.IS', 'TKFEN.IS',
    'TKNKA.IS', 'TKNSA.IS', 'TLMAN.IS', 'TMPOL.IS', 'TMSN.IS', 'TNZTP.IS', 'TOASO.IS',
    'TRALT.IS', 'TRCAS.IS', 'TRENJ.IS', 'TRGYO.IS', 'TRHOL.IS', 'TRILC.IS', 'TRMET.IS',
    'TSGYO.IS', 'TSKB.IS', 'TSPOR.IS', 'TTKOM.IS', 'TTRAK.IS', 'TUCLK.IS', 'TUKAS.IS',
    'TUPRS.IS', 'TUREX.IS', 'TURGG.IS', 'TURSG.IS', 'UCAYM.IS', 'UFUK.IS', 'ULAS.IS',
    'ULKER.IS', 'ULUFA.IS', 'ULUSE.IS', 'ULUUN.IS', 'UMPAS.IS', 'UNLU.IS', 'USAK.IS',
    'USHOL.IS', 'VAKBN.IS', 'VAKFA.IS', 'VAKFN.IS', 'VAKKO.IS', 'VANGD.IS', 'VBTYZ.IS',
    'VERTU.IS', 'VERUS.IS', 'VESBE.IS', 'VESTL.IS', 'VEYAS.IS', 'VKFYO.IS', 'VKGYO.IS',
    'VKING.IS', 'VRGYO.IS', 'VSNMD.IS', 'YAPRK.IS', 'YATAS.IS', 'YAYLA.IS', 'YBTAS.IS',
    'YEOTK.IS', 'YESIL.IS', 'YGGYO.IS', 'YIGIT.IS', 'YKBNK.IS', 'YKSLN.IS', 'YONGA.IS',
    'YUNSA.IS', 'YYAPI.IS', 'YYLGD.IS', 'ZEDUR.IS', 'ZERGY.IS', 'ZGYO.IS', 'ZOREN.IS', 'ZRGYO.IS'
]

tickers = list(set([t.replace('.IS', '') for t in ham_tickers]))
results = []

for periyot_adi, aktif_mi in TARAMA_YAPILACAK_PERIYOTLAR.items():
    if not aktif_mi:
        continue

    print(f"\n🔍 '{periyot_adi}' periyodu için tarama başladı...")
    ayar = PERIYOT_AYARLARI[periyot_adi]

    for ticker in tqdm(tickers, desc=f"{periyot_adi} Taranıyor"):
        try:
            ticker_symbol = f"{ticker}.IS"
            df = yf.download(ticker_symbol, period=ayar["period"], interval=ayar["interval"], progress=False)

            if df.empty or len(df) < 100:
                continue

            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.droplevel(1)

            if ayar["resample_rule"]:
                df = df.resample(ayar["resample_rule"]).agg({
                    'Open': 'first',
                    'High': 'max',
                    'Low': 'min',
                    'Close': 'last',
                    'Volume': 'sum'
                }).dropna()

                if len(df) < 100:
                    continue

            curr_vol = float(df['Volume'].iloc[-1])
            if curr_vol == 0:
                continue

            # --- İNDİKATÖR HESAPLAMALARI ---
            ema20 = df['Close'].ewm(span=EMA_TREND, adjust=False).mean()
            
            # CCI Hesabı
            tp = (df['High'] + df['Low'] + df['Close']) / 3
            sma_tp = tp.rolling(window=CCI_PERIYOT).mean()
            mad = tp.rolling(window=CCI_PERIYOT).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
            cci = (tp - sma_tp) / (0.015 * mad)

            # RSI Hesabı (14 Periyot)
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=RSI_PERIYOT).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=RSI_PERIYOT).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))

            # 52 Periyotluk Kijun-sen Hesabı
            fifty_two_high = df['High'].rolling(window=52).max()
            fifty_two_low = df['Low'].rolling(window=52).min()
            kijun_52 = (fifty_two_high + fifty_two_low) / 2

            # Chikou Span ve Kijun-52 Kaydırma Hizalaması (26 bar geriye)
            close_shift26 = df['Close'].shift(26)
            kijun_52_shift26 = kijun_52.shift(26)

            close_curr = float(df['Close'].iloc[-1])
            ema20_curr = float(ema20.iloc[-1])
            prev_cci = float(cci.iloc[-2])
            curr_cci = float(cci.iloc[-1])
            curr_rsi = float(rsi.iloc[-1])

            chikou_curr = float(close_shift26.iloc[-1])
            kijun52_curr = float(kijun_52_shift26.iloc[-1])

            chikou_prev = float(close_shift26.iloc[-2])
            kijun52_prev = float(kijun_52_shift26.iloc[-2])

            chikou_prev2 = float(close_shift26.iloc[-3])
            kijun52_prev2 = float(kijun_52_shift26.iloc[-3])

            # --- FİLTRELER ---

            # 1. Kural: CCI -100'ün üzerinde ve yükselişte olmalı
            if not ((curr_cci > -100) and (curr_cci > prev_cci)):
                continue

            # 2. Kural: Trend Filtresi (Fiyat EMA 20'nin üzerinde olmalı)
            if TREND_FILTRESI_AKTIF:
                if close_curr < ema20_curr:
                    continue  

            # 3. Kural: Hacim Filtresi (Son hacim 10 mumluk ortalamadan büyük olmalı)
            if HACIM_FILTRESI_AKTIF:
                vol_sma = df['Volume'].rolling(window=HACIM_ORT_PERIYOT).mean()
                vol_sma_curr = float(vol_sma.iloc[-1])
                if curr_vol <= vol_sma_curr:
                    continue  

            # 4. Kural: Chikou Span - 52 Periyotluk Kijun-Sen Kesişim Filtresi
            if CHIKOU_KIJUN_FILTRESI_AKTIF:
                kesisim_sarti = (chikou_curr > kijun52_curr and chikou_prev <= kijun52_prev) or \
                                (chikou_prev > kijun52_prev and chikou_prev2 <= kijun52_prev2)
                
                if not kesisim_sarti:
                    continue

            # 5. Kural: RSI Filtresi (RSI 65 ile 71 arasında olmalı)
            if RSI_FILTRESI_AKTIF:
                if not (65 <= curr_rsi <= 71):
                    continue

            hacim_oran = round(curr_vol / float(df['Volume'].rolling(10).mean().iloc[-1]), 2)
            bilgi = {
                'Zaman Dilimi': periyot_adi,
                'Hisse': ticker,
                'Son Kapanis': round(close_curr, 2),
                'EMA 20': round(ema20_curr, 2),
                'Chikou (Geride)': round(chikou_curr, 2),
                'Kijun-52 (Geride)': round(kijun52_curr, 2),
                'Son CCI': round(curr_cci, 2),
                'Son RSI': round(curr_rsi, 2),
                'Hacim/Ort': hacim_oran,
                'Tarih/Saat': str(df.index[-1])
            }
            results.append(bilgi)

            tv_link = f"https://www.tradingview.com/chart/?symbol=BIST:{ticker}"
            msg = (
                f"🚨 *CHIKOU - KIJUN & RSI SİNYALİ*\n"
                f"*Hisse:* `{ticker}`\n"
                f"*Periyot:* {periyot_adi}\n"
                f"*Fiyat Kapanış:* {close_curr}\n"
                f"*EMA 20:* {ema20_curr:.2f}\n"
                f"*Chikou Değeri:* {chikou_curr:.2f}\n"
                f"*Kijun-52 Seviyesi:* {kijun52_curr:.2f} (Yukarı Kesti)\n"
                f"*CCI:* {curr_cci:.2f}\n"
                f"*RSI (14):* {curr_rsi:.2f} (65-71 Arası)\n"
                f"📊 *Hacim Durumu:* Ortalamanın {hacim_oran}x katı\n\n"
                f"📈 [TradingView Grafiği Aç]({tv_link})"
            )
            telegram_mesaj_gonder(msg)
            time.sleep(1.1)

        except Exception as e:
            continue

if results:
    df_results = pd.DataFrame(results)
    df_results = df_results.sort_values(by=['Zaman Dilimi', 'Hisse']).reset_index(drop=True)
    excel_filename = "Chikou_Kijun52_RSI_Sonuclari.xlsx"
    df_results.to_excel(excel_filename, index=False)
    print(f"\n✅ Tarama tamamlandı! Toplam {len(results)} hisse tüm şartları (Chikou-Kijun ve RSI 65-71) sağlayarak yakalandı.")
else:
    print("\n⚠️ Seçili periyotlarda bu şartları sağlayan hisse bulunamadı.")
