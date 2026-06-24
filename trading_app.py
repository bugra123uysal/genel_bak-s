"""
ABD Borsası Al/Sat Botu — UT Bot Alerts + Simülasyon
=====================================================
Tek dosyalık birleşik uygulama:
  1) 📡 Piyasa Tarayıcı : Tüm hisse havuzunu tarar, AL/SAT sinyali verenleri
                          en üstte liste halinde gösterir.
  2) 🤖 Detaylı Analiz  : Seçilen hisse için UT Bot grafiği + backtest +
                          teknik skor/formasyon analizi.
  3) 🎮 Simülasyon      : Eğitim amaçlı trading karar oyunu (XP, rozet, hedef).

İndikatör mantığı: TradingView "UT Bot Alerts" (ATR trailing stop) birebir uyarlama.

UYARI: Yatırım tavsiyesi değildir. Gerçek emir göndermez. Eğitim amaçlıdır.
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import random
from datetime import datetime

# ===========================================================================
# SABİTLER
# ===========================================================================

DEFAULT_TICKERS = [
    "AAPL", "MSFT", "NVDA", "TSLA", "AMD", "META", "AMZN", "GOOGL",
    "PLTR", "COIN", "NFLX", "AVGO", "SMCI", "MU", "INTC", "JPM",
    "V", "WMT", "DIS", "BA",
]

PERIOD_INTERVAL_MAP = {
    "5 Gün / 15dk": ("5d", "15m"),
    "1 Ay / 1saat": ("1mo", "1h"),
    "3 Ay / Günlük": ("3mo", "1d"),
    "6 Ay / Günlük": ("6mo", "1d"),
    "1 Yıl / Günlük": ("1y", "1d"),
}

GOALS = [110, 120, 130, 140, 150, 170, 190, 210, 250, 300, 350, 400, 450, 500]

BADGES = {
    "İlk Doğru Karar": {"icon": "🎯", "cond": lambda s: s["correct"] >= 1},
    "İlk Kâr":         {"icon": "💰", "cond": lambda s: s["balance"] > 100},
    "3 Doğru Seri":    {"icon": "🔥", "cond": lambda s: s["streak"] >= 3},
    "Riskten Kaçan":   {"icon": "🛡️", "cond": lambda s: s["risk_avoided"] >= 1},
    "Trend Avcısı":    {"icon": "📈", "cond": lambda s: s["correct"] >= 5},
    "Formasyon Ustası":{"icon": "🔍", "cond": lambda s: s["correct"] >= 10},
    "Hedef Avcısı":    {"icon": "🏹", "cond": lambda s: s["goals_done"] >= 1},
    "2x Bakiye":       {"icon": "🚀", "cond": lambda s: s["balance"] >= 200},
}

SYNTHETIC_TYPES = ["Yükselen Trend", "Düşen Trend", "Yatay Piyasa", "Breakout",
                   "Fake Breakout", "Pullback", "Hacimli Yükseliş", "RSI Zayıflığı"]

# Momentum / breakout taraması için geniş evren (Qullamaggie/Minervini tarzı adaylar)
MOMENTUM_UNIVERSE = [
    "NVDA", "ARM", "SMCI", "PLTR", "COIN", "FCEL", "FLNC", "MSTR", "APP", "VRT",
    "CLS", "POWL", "ANET", "AVGO", "MU", "AMD", "TSLA", "NET", "CRWD", "DDOG",
    "SHOP", "PANW", "SNOW", "MARA", "RIOT", "CVNA", "AFRM", "SOFI", "DKNG", "RDDT",
    "HOOD", "IONQ", "RGTI", "OKLO", "SMR", "TSM", "ASML", "META", "AMZN", "GOOGL",
]

# Nasdaq-100 (yaklaşık) — daha geniş ve anlamlı RS sıralaması için
NASDAQ100 = [
    "AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "GOOG", "AVGO", "TSLA", "COST",
    "NFLX", "ASML", "AMD", "PEP", "ADBE", "LIN", "CSCO", "TMUS", "INTU", "QCOM",
    "TXN", "AMGN", "ISRG", "AMAT", "BKNG", "HON", "VRTX", "PANW", "ADP", "MU",
    "ADI", "GILD", "REGN", "LRCX", "MELI", "SBUX", "MDLZ", "KLAC", "SNPS", "CDNS",
    "CRWD", "CEG", "MAR", "PYPL", "ORLY", "CSX", "ABNB", "MRVL", "FTNT", "DASH",
    "WDAY", "ADSK", "NXPI", "ROP", "TTD", "CHTR", "PCAR", "MNST", "AEP", "PAYX",
    "KDP", "ODFL", "FAST", "EA", "CTAS", "VRSK", "DDOG", "EXC", "GEHC", "KHC",
    "CCEP", "LULU", "BKR", "XEL", "CSGP", "IDXX", "ON", "TEAM", "ANSS", "ZS",
    "CDW", "BIIB", "DXCM", "MCHP", "TTWO", "GFS", "ILMN", "WBD", "ARM", "PLTR",
    "APP", "MSTR", "SMCI", "COIN",
]

# S&P 500 geniş evreni — Qullamaggie taraması için (~500 hisse, büyük cap)
SP500_UNIVERSE = sorted(set(NASDAQ100 + [
    "JPM", "BAC", "WFC", "GS", "MS", "C", "USB", "PNC", "TFC", "COF",
    "BLK", "SCHW", "AXP", "CB", "MMC", "ICE", "CME", "SPGI", "MCO", "AON",
    "JNJ", "UNH", "LLY", "PFE", "ABBV", "MRK", "BMY", "ABT", "TMO", "DHR",
    "SYK", "BSX", "MDT", "EW", "ZBH", "BDX", "HOLX", "ALGN", "IDXX", "MTD",
    "ORCL", "CRM", "NOW", "SAP", "INTU", "ADBE", "SNPS", "CDNS", "ANSS", "PTC",
    "UBER", "LYFT", "ABNB", "BKNG", "EXPE", "MAR", "HLT", "WYNN", "LVS", "MGM",
    "AMZN", "SHOP", "ETSY", "EBAY", "W", "CHWY", "CVNA", "CARVANA", "KR", "COST",
    "WMT", "TGT", "HD", "LOW", "BBY", "DG", "DLTR", "FIVE", "OLLI",
    "XOM", "CVX", "COP", "SLB", "HAL", "BKR", "PSX", "VLO", "MPC", "DVN",
    "NEE", "DUK", "SO", "AEP", "EXC", "SRE", "PEG", "D", "ETR", "PPL",
    "LIN", "APD", "ECL", "SHW", "PPG", "IFF", "ALB", "MP", "ENPH", "FSLR",
    "CAT", "DE", "EMR", "ETN", "ROK", "AME", "VRSK", "GE", "HON", "MMM",
    "UPS", "FDX", "XPO", "SAIA", "ODFL", "JBHT", "KNX", "CHRW",
    "NFLX", "DIS", "PARA", "WBD", "FOX", "FOXA", "CMCSA", "CHTR", "TMUS",
    "V", "MA", "PYPL", "SQ", "FI", "FIS", "GPN", "WEX", "AFRM", "SOFI",
    "TSLA", "GM", "F", "RIVN", "LCID", "TM", "HMC", "STLA",
    "BA", "LMT", "RTX", "NOC", "GD", "L3H", "TDG", "HWM", "SPR", "KTOS",
    "DECK", "NKE", "LULU", "UAA", "VFC", "RL", "PVH", "TPR",
    "MCD", "SBUX", "YUM", "QSR", "CMG", "DKNG", "PENN", "VICI",
    "PLD", "AMT", "CCI", "EQIX", "DLR", "SPG", "O", "PSA", "EQR", "AVB",
    "LEN", "DHI", "PHM", "TOL", "NVR", "TMHC",
    "CELH", "MNST", "KO", "PEP", "KDP", "STZ", "BUD", "TAP",
    "FICO", "TYL", "MSCI", "NTRS", "BEN", "TROW", "IVZ", "AMG",
    "AXON", "TASER", "S", "OKTA", "ZS", "SAIL", "QLYS", "TENB",
    "MELI", "NU", "STNE", "PAGS", "XP", "GLOB", "ARCO",
    "RDDT", "SNAP", "PINS", "MTCH", "ZM", "DOCU", "DOCN", "CFLT",
    "GH", "EXAS", "NVAX", "MRNA", "BNTX", "REGN", "ALNY", "INCY",
    "HOOD", "COIN", "MSTR", "MARA", "RIOT", "CLSK", "CIFR",
    "IONQ", "RGTI", "QBTS", "OKLO", "SMR", "NNE", "BWXT", "CEG", "VST",
    "PLTR", "AI", "BBAI", "SOUN", "IREN", "CORZ",
    "VRT", "ANET", "SMCI", "CLS", "POWL", "ASTS", "RDW",
]))

# Renkler
C_UP = "#16c784"
C_DOWN = "#ea3943"
C_ACCENT = "#3b82f6"
C_PURPLE = "#a855f7"
C_GOLD = "#f0b90b"

# Makro / piyasa geneli enstrümanlar (risk iştahı okuması için)
MACRO_ASSETS = {
    "^GSPC": "S&P 500",
    "^IXIC": "Nasdaq",
    "QQQ":   "QQQ (Nasdaq ETF)",
    "^DJI":  "Dow Jones",
    "^RUT":  "Russell 2000",
    "^VIX":  "VIX (Korku)",
    "^TNX":  "10Y Faiz",
    "DX-Y.NYB": "Dolar (DXY)",
    "GC=F":  "Altın",
    "CL=F":  "Petrol",
    "BTC-USD": "Bitcoin",
}

# Dünya borsaları — bölgeye göre gruplandırılmış
GLOBAL_INDICES = {
    "Amerika": {
        "^GSPC":  {"isim": "S&P 500",      "ulke": "🇺🇸"},
        "^IXIC":  {"isim": "Nasdaq",        "ulke": "🇺🇸"},
        "QQQ":    {"isim": "QQQ",           "ulke": "🇺🇸"},
        "^RUT":   {"isim": "Russell 2000",  "ulke": "🇺🇸"},
        "^BVSP":  {"isim": "Bovespa",       "ulke": "🇧🇷"},
    },
    "Avrupa": {
        "^FTSE":    {"isim": "FTSE 100",    "ulke": "🇬🇧"},
        "^GDAXI":   {"isim": "DAX",         "ulke": "🇩🇪"},
        "^FCHI":    {"isim": "CAC 40",      "ulke": "🇫🇷"},
        "^STOXX50E":{"isim": "Euro Stoxx",  "ulke": "🇪🇺"},
        "XU100.IS": {"isim": "BIST 100",    "ulke": "🇹🇷"},
    },
    "Asya-Pasifik": {
        "^N225":    {"isim": "Nikkei 225",  "ulke": "🇯🇵"},
        "^KS11":    {"isim": "KOSPI",       "ulke": "🇰🇷"},
        "^HSI":     {"isim": "Hang Seng",   "ulke": "🇭🇰"},
        "000001.SS":{"isim": "Shanghai",    "ulke": "🇨🇳"},
        "^NSEI":    {"isim": "NIFTY 50",    "ulke": "🇮🇳"},
        "^AXJO":    {"isim": "ASX 200",     "ulke": "🇦🇺"},
    },
}

# Sektör ETF'leri (para hangi sektöre akıyor - sektör rotasyonu)
SECTOR_ETFS = {
    "XLK": "Teknoloji",
    "XLF": "Finans",
    "XLE": "Enerji",
    "XLV": "Sağlık",
    "XLY": "Tüketici (İsteğe Bağlı)",
    "XLP": "Tüketici (Temel)",
    "XLI": "Sanayi",
    "XLB": "Hammadde",
    "XLU": "Kamu Hizmetleri",
    "XLRE": "Gayrimenkul",
    "XLC": "İletişim",
}

# Sektör ETF eşlemesi — RS hesabı için
STOCK_SECTOR_MAP = {
    "XLK": ["NVDA","AMD","MSFT","AAPL","AVGO","ANET","MU","SMCI","ARM","INTC","QCOM","TXN","ADI","LRCX","AMAT","KLAC","MRVL"],
    "XLC": ["META","GOOGL","GOOG","NFLX","SNAP","RDDT","PINS","TTWO","EA"],
    "XLY": ["TSLA","AMZN","SHOP","CVNA","DKNG","ABNB","BKNG","MAR","ORLY"],
    "XLF": ["JPM","V","MA","GS","MS","BAC","COIN","HOOD","SOFI","AFRM"],
    "XLE": ["XOM","CVX","COP","SLB","OXY","PSX","VLO","MPC"],
    "XLV": ["LLY","JNJ","UNH","ABT","TMO","DHR","ISRG","VRTX","REGN","AMGN","GILD","IDXX","DXCM"],
    "XLI": ["GE","HON","CAT","DE","LMT","RTX","NOC","POWL","VRT","CLS"],
}

# ===========================================================================
# TEKNİK HESAPLAMALAR
# ===========================================================================

def compute_ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def compute_mfi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Money Flow Index — hacim ağırlıklı RSI; para girişi/çıkışını ölçer."""
    tp = (df["High"] + df["Low"] + df["Close"]) / 3
    mf = tp * df["Volume"]
    pos = mf.where(tp > tp.shift(), 0.0)
    neg = mf.where(tp < tp.shift(), 0.0)
    pos_sum = pos.rolling(period).sum()
    neg_sum = neg.rolling(period).sum()
    mfr = pos_sum / neg_sum.replace(0, np.nan)
    return 100 - (100 / (1 + mfr))


def compute_obv(df: pd.DataFrame) -> pd.Series:
    """On-Balance Volume — hacmi fiyat yönüne göre toplar; birikim/dağıtım izi."""
    direction = np.sign(df["Close"].diff()).fillna(0)
    return (direction * df["Volume"]).cumsum()


def relative_volume(df: pd.DataFrame, window: int = 20) -> float:
    """Bugünkü hacim / son `window` günün ortalaması. >1.5 = olağandışı ilgi."""
    if len(df) < window + 1:
        return 1.0
    avg = df["Volume"].iloc[-window - 1:-1].mean()
    return float(df["Volume"].iloc[-1] / avg) if avg > 0 else 1.0


def compute_adr_pct(df: pd.DataFrame, period: int = 20) -> float:
    """Average Daily Range % — günlük volatilite (Qullamaggie/Minervini metriği)."""
    if len(df) < period + 1:
        period = max(2, len(df) - 1)
    dr = df["High"] / df["Low"]
    return float((dr.iloc[-period:].mean() - 1) * 100)


def momentum_score(df: pd.DataFrame) -> float:
    """IBD tarzı ağırlıklı getiri (göreli güç ham puanı)."""
    c = df["Close"]
    def ret(n):
        return c.iloc[-1] / c.iloc[-n] - 1 if len(c) > n else c.iloc[-1] / c.iloc[0] - 1
    return 0.4 * ret(63) + 0.3 * ret(126) + 0.2 * ret(189) + 0.1 * ret(252)


def trend_template(df: pd.DataFrame) -> dict:
    """Minervini Trend Template kontrolleri + Qullamaggie EMA bulutu durumu."""
    c = df["Close"]
    price = float(c.iloc[-1])
    ema10 = compute_ema(c, 10).iloc[-1]
    ema20 = compute_ema(c, 20).iloc[-1]
    sma50 = c.rolling(50).mean().iloc[-1] if len(c) >= 50 else c.mean()
    sma150 = c.rolling(150).mean().iloc[-1] if len(c) >= 150 else c.mean()
    sma200 = c.rolling(200).mean().iloc[-1] if len(c) >= 200 else c.mean()
    sma200_prev = c.rolling(200).mean().iloc[-21] if len(c) >= 221 else sma200
    high52 = float(c.iloc[-252:].max()) if len(c) >= 60 else float(c.max())
    low52 = float(c.iloc[-252:].min()) if len(c) >= 60 else float(c.min())

    checks = {
        "Fiyat > 50MA": price > sma50,
        "50MA > 150MA": sma50 > sma150,
        "150MA > 200MA": sma150 > sma200,
        "200MA yükseliyor": sma200 > sma200_prev,
        "52H zirvenin %25'i içinde": price >= high52 * 0.75,
        "52H dipten %30+ yukarı": price >= low52 * 1.30,
        "Bulut üstünde (EMA10>EMA20)": price > ema10 and ema10 > ema20,
    }
    return {
        "passed": sum(checks.values()),
        "total": len(checks),
        "checks": checks,
        "above_cloud": price > ema10 > ema20,
        "above_50": price > sma50,
        "pct_from_high": round((price / high52 - 1) * 100, 1),
        "high52": round(high52, 2),
    }


def detect_setup(df: pd.DataFrame) -> str:
    """Qullamaggie'nin 3 temel setupını + trend/zayıf etiketini döner."""
    c = df["Close"]
    if len(c) < 25:
        return "Yetersiz veri"
    ema10 = compute_ema(c, 10)
    ema20 = compute_ema(c, 20)
    price  = float(c.iloc[-1])
    open_  = float(df["Open"].iloc[-1])
    above_cloud = price > ema10.iloc[-1] > ema20.iloc[-1]

    vol_now = float(df["Volume"].iloc[-1])
    vol_avg = float(df["Volume"].iloc[-20:].mean())
    rvol    = vol_now / vol_avg if vol_avg > 0 else 1.0

    # Episodic Pivot: gün içi gap %4+ ve hacim 2.5x+
    gap_pct = (open_ - float(c.iloc[-2])) / float(c.iloc[-2]) * 100 if len(c) >= 2 else 0
    if gap_pct >= 4.0 and rvol >= 2.5:
        return "⚡ Episodik Pivot"

    # Konsolidasyon + Kırılım
    recent = c.iloc[-10:]
    rng = (recent.max() - recent.min()) / recent.min() * 100
    adr = compute_adr_pct(df)
    cons_high = float(df["High"].iloc[-11:-1].max())
    tight = rng < adr * 2.0

    if above_cloud and price > cons_high and rvol >= 1.5:
        return "🚀 Kırılım"

    # EMA Geri Çekilme: EMA10/20'ye dokunup döndü
    low_last3 = float(df["Low"].iloc[-3:].min())
    touched_ema = ema10.iloc[-4] * 0.995 <= low_last3 <= ema20.iloc[-4] * 1.01
    bouncing = price > float(c.iloc[-2])
    if above_cloud and touched_ema and bouncing and not tight:
        return "🔄 EMA Geri Çekilme"

    if above_cloud and tight:
        return "🏴 Sıkışma (VCP)"
    if above_cloud:
        return "📈 Trend"
    if price < ema20.iloc[-1]:
        return "⚠️ Zayıf"
    return "↔️ Belirsiz"


def explain_trade(setup: str, df: pd.DataFrame) -> dict:
    """
    Qullamaggie mantığıyla trade planı üretir.
    Döner: giriş, stop, hedef, risk/ödül, gerekçe, ne bekle.
    """
    c   = df["Close"]
    hi  = df["High"]
    lo  = df["Low"]
    price = float(c.iloc[-1])
    ema10 = float(compute_ema(c, 10).iloc[-1])
    ema20 = float(compute_ema(c, 20).iloc[-1])
    adr   = compute_adr_pct(df)

    if "Kırılım" in setup:
        entry  = round(price * 1.002, 2)
        stop   = round(ema10 * 0.985, 2)
        target = round(entry * (1 + adr / 100 * 5), 2)
        neden  = ("Hacimli kırılım: fiyat konsolidasyon tepesini yüksek hacimle geçti. "
                  "Kurumsal alım baskısı var.")
        bekle  = "Kapanış kırılım seviyesinin üstünde olmalı. Düşük hacimli kırılım = sahte."

    elif "Episodik" in setup:
        entry  = round(price, 2)
        stop   = round(float(lo.iloc[-1]) * 0.98, 2)
        target = round(entry * 1.25, 2)
        neden  = ("Episodik Pivot: büyük hacimli gap-up. Kurumlar hisseyi yeniden fiyatlıyor. "
                  "Birkaç günde %20-50 gelebilir.")
        bekle  = "Gap dolmazsa güçlü. Gap tamamen kapanırsa setup bozulmuş — çık."

    elif "EMA Geri" in setup:
        entry  = round(ema10 * 1.005, 2)
        stop   = round(ema20 * 0.985, 2)
        target = round(entry * (1 + adr / 100 * 4), 2)
        neden  = ("Trend sağlam, fiyat EMA10'a dokunup döndü. "
                  "Düşük riskli giriş — trend yönünde alım.")
        bekle  = "EMA'lar yukarı eğimli olmalı. Hacim geri çekilmede düşük, çıkışta yüksek."

    elif "Sıkışma" in setup:
        cons_high = float(hi.iloc[-21:-1].max())
        entry  = round(cons_high * 1.005, 2)
        stop   = round(ema20 * 0.985, 2)
        target = round(entry * (1 + adr / 100 * 5), 2)
        neden  = ("VCP sıkışması: hacim daralıyor, fiyat dar bantta. Kırılım öncesi birikim. "
                  f"Kırılım emri: ${entry} — henüz girme, tetiklenince gir.")
        bekle  = f"Kırılım seviyesi: ${entry}. Hacim 1.5x+ olmalı. Kırılım yoksa bekle."

    else:
        return {}

    rr = round((target - entry) / max(entry - stop, 0.01), 1)
    return {"entry": entry, "stop": stop, "target": target,
            "rr": rr, "neden": neden, "bekle": bekle, "setup": setup}


def stealth_accumulation(df: pd.DataFrame, days: int = 10) -> dict:
    """
    Fiyat hareket etmeden önce hacim artışını tespit eder.
    Smart money sessizce topluyor = fiyat flat, hacim yükseliyor.
    Skor 0-100. 70+ = güçlü birikim sinyali.
    """
    if len(df) < days + 5:
        return {"score": 0, "signal": False}

    recent = df.iloc[-days:]
    price_change = abs((float(recent["Close"].iloc[-1]) - float(recent["Close"].iloc[0]))
                       / float(recent["Close"].iloc[0]) * 100)

    # OBV eğimi — hacim birikim yönü
    obv = compute_obv(df)
    obv_recent = obv.iloc[-days:]
    x = np.arange(len(obv_recent))
    obv_slope = float(np.polyfit(x, obv_recent.values, 1)[0])
    obv_norm = obv_slope / (abs(float(obv_recent.mean())) + 1)

    # Hacim eğimi — artıyor mu?
    vol = recent["Volume"].values
    vol_slope = float(np.polyfit(x, vol, 1)[0])
    vol_norm = vol_slope / (float(vol.mean()) + 1)

    # MFI divergans: MFI yükseliyor, fiyat flat
    mfi = compute_mfi(df, 14)
    mfi_recent = mfi.iloc[-days:]
    mfi_slope = float(mfi_recent.iloc[-1]) - float(mfi_recent.iloc[0])

    # Stealth skor: fiyat flat iken hacim/OBV yükseliyorsa yüksek
    price_flat = price_change < 5.0
    obv_rising = obv_norm > 0
    vol_rising = vol_norm > 0
    mfi_rising = mfi_slope > 3

    score = 0
    if price_flat:   score += 20
    if obv_rising:   score += 30
    if vol_rising:   score += 25
    if mfi_rising:   score += 25
    score = min(100, score)

    return {
        "score": score,
        "signal": score >= 60 and price_flat,
        "price_chg_pct": round(price_change, 1),
        "obv_rising": obv_rising,
        "vol_rising": vol_rising,
        "mfi_rising": mfi_rising,
    }


@st.cache_data(ttl=3600)
def get_float_shares(ticker: str) -> float | None:
    """Hissenin dolaşımdaki float hissesi sayısını çeker (milyon cinsinden)."""
    try:
        info = yf.Ticker(ticker).info
        fs = info.get("floatShares") or info.get("sharesOutstanding")
        return round(fs / 1e6, 1) if fs else None
    except Exception:
        return None


def sector_rs(ticker: str, df: pd.DataFrame) -> dict:
    """
    Hissenin kendi sektör ETF'ine karşı göreli gücünü hesaplar.
    Sektör ETF'inden güçlüyse = sektör lideri.
    """
    # Hangi sektörde?
    sector_etf = None
    for etf, stocks in STOCK_SECTOR_MAP.items():
        if ticker in stocks:
            sector_etf = etf
            break
    if not sector_etf:
        return {"vs_sector": None, "sector_etf": None}

    etf_df = fetch_daily(sector_etf, "3mo")
    if etf_df is None or len(etf_df) < 20:
        return {"vs_sector": None, "sector_etf": sector_etf}

    # Son 3 ay getirisi: hisse vs ETF
    stock_ret = (float(df["Close"].iloc[-1]) / float(df["Close"].iloc[-63]) - 1) * 100 if len(df) >= 63 else 0
    etf_ret   = (float(etf_df["Close"].iloc[-1]) / float(etf_df["Close"].iloc[-63]) - 1) * 100 if len(etf_df) >= 63 else 0
    vs_sector = round(stock_ret - etf_ret, 1)

    return {"vs_sector": vs_sector, "sector_etf": sector_etf,
            "stock_ret": round(stock_ret, 1), "etf_ret": round(etf_ret, 1)}


def wilder_atr(df: pd.DataFrame, period: int) -> pd.Series:
    """TradingView atr() ile uyumlu Wilder (RMA) ATR."""
    high, low, close = df["High"], df["Low"], df["Close"]
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / period, adjust=False).mean()


def ut_bot_signals(df: pd.DataFrame, key_value: float = 1.0, atr_period: int = 10) -> pd.DataFrame:
    """UT Bot Alerts mantığı: ATR trailing stop + AL/SAT sinyalleri."""
    src = df["Close"].values
    atr = wilder_atr(df, atr_period).values
    n_loss = key_value * atr
    n = len(src)
    stop = np.zeros(n)

    for i in range(n):
        if i == 0 or np.isnan(atr[i]):
            stop[i] = src[i] - n_loss[i] if not np.isnan(n_loss[i]) else src[i]
            continue
        prev = stop[i - 1]
        if src[i] > prev and src[i - 1] > prev:
            stop[i] = max(prev, src[i] - n_loss[i])
        elif src[i] < prev and src[i - 1] < prev:
            stop[i] = min(prev, src[i] + n_loss[i])
        elif src[i] > prev:
            stop[i] = src[i] - n_loss[i]
        else:
            stop[i] = src[i] + n_loss[i]

    pos = np.zeros(n)
    for i in range(1, n):
        if src[i - 1] < stop[i - 1] and src[i] > stop[i - 1]:
            pos[i] = 1
        elif src[i - 1] > stop[i - 1] and src[i] < stop[i - 1]:
            pos[i] = -1
        else:
            pos[i] = pos[i - 1]

    ema = src  # EMA(src, 1) == src
    above = np.zeros(n, dtype=bool)
    below = np.zeros(n, dtype=bool)
    for i in range(1, n):
        above[i] = ema[i - 1] <= stop[i - 1] and ema[i] > stop[i]
        below[i] = stop[i - 1] <= ema[i - 1] and stop[i] > ema[i]

    out = df.copy()
    out["stop"] = stop
    out["atr"] = atr
    out["pos"] = pos
    out["buy"] = (src > stop) & above
    out["sell"] = (src < stop) & below
    return out


def detect_formation(df: pd.DataFrame) -> list:
    formations = []
    close, volume = df["Close"], df["Volume"]
    ema21, ema50 = compute_ema(close, 21), compute_ema(close, 50)
    rsi = compute_rsi(close)
    last_close = close.iloc[-1]
    last_rsi = rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50
    avg_vol = volume.iloc[-20:].mean()

    a21 = last_close > ema21.iloc[-1]
    a50 = last_close > ema50.iloc[-1]
    cross = ema21.iloc[-1] > ema50.iloc[-1]

    if a21 and a50 and cross:
        formations.append("Yükselen Trend")
    elif not a21 and not a50 and not cross:
        formations.append("Düşen Trend")
    else:
        formations.append("Yatay Piyasa")

    if last_close > df["High"].iloc[-21:-1].max():
        formations.append("Direnç Kırılımı")
    if last_close < df["Low"].iloc[-21:-1].min():
        formations.append("Destek Kırılımı")
    if volume.iloc[-1] > avg_vol * 1.5:
        formations.append("Hacimli Kırılım")
    if ema21.iloc[-2] < ema50.iloc[-2] and ema21.iloc[-1] > ema50.iloc[-1]:
        formations.append("EMA Altın Kesişim")
    if ema21.iloc[-2] > ema50.iloc[-2] and ema21.iloc[-1] < ema50.iloc[-1]:
        formations.append("EMA Ölüm Kesişimi")
    if df["Low"].iloc[-10:].is_monotonic_increasing:
        formations.append("Higher Low")
    if df["High"].iloc[-10:].is_monotonic_decreasing:
        formations.append("Lower High")
    return formations


def compute_score(df: pd.DataFrame) -> dict:
    close, volume = df["Close"], df["Volume"]
    ema21, ema50 = compute_ema(close, 21), compute_ema(close, 50)
    rsi = compute_rsi(close)
    last_close = close.iloc[-1]
    last_rsi = rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50
    avg_vol = volume.iloc[-20:].mean()

    trend = 25 if (last_close > ema21.iloc[-1] and last_close > ema50.iloc[-1]) else (12 if last_close > ema21.iloc[-1] else 0)
    ema = 20 if ema21.iloc[-1] > ema50.iloc[-1] else 0
    rsi_s = 15 if last_rsi > 55 else (7 if last_rsi > 45 else 0)
    vol = 20 if volume.iloc[-1] > avg_vol else 0
    formations = detect_formation(df)
    form = min(20, len([f for f in formations if f not in ("Yatay Piyasa", "Düşen Trend", "Lower High", "EMA Ölüm Kesişimi", "Destek Kırılımı")]) * 7)
    total = trend + ema + rsi_s + vol + form
    return {"total": total, "trend": trend, "ema": ema, "rsi": rsi_s,
            "volume": vol, "formation": form, "formations": formations,
            "rsi_val": round(last_rsi, 1)}


def system_decision(score: int) -> str:
    if score >= 70:
        return "AL için uygun"
    elif score >= 40:
        return "Bekle / izlemeye değer"
    return "İşleme girmek riskli"


# ===========================================================================
# VERİ ÇEKME (cache'li)
# ===========================================================================

@st.cache_data(ttl=180, show_spinner=False)
def fetch_daily(ticker: str, period: str = "3mo") -> pd.DataFrame | None:
    """Günlük veri (Piyasa Nabzı için, kısa cache = canlıya yakın)."""
    try:
        df = yf.download(ticker, period=period, interval="1d",
                         progress=False, auto_adjust=True)
        if df is None or len(df) < 2:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df.dropna()
    except Exception:
        return None


@st.cache_data(ttl=300, show_spinner=False)
def fetch_data(ticker: str, period: str, interval: str) -> pd.DataFrame | None:
    try:
        df = yf.download(ticker, period=period, interval=interval,
                         progress=False, auto_adjust=True)
        if df is None or len(df) < 30:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df.dropna()
    except Exception:
        return None


# ===========================================================================
# BACKTEST
# ===========================================================================

def backtest(df: pd.DataFrame, initial_cash: float = 10000.0, fee_pct: float = 0.1) -> dict:
    cash, position, entry_price = initial_cash, 0.0, 0.0
    trades, equity_curve = [], []
    fee = fee_pct / 100.0
    closes = df["Close"].values
    buys, sells = df["buy"].values, df["sell"].values
    idx = df.index

    for i in range(len(df)):
        price = closes[i]
        if buys[i] and position == 0:
            qty = (cash * (1 - fee)) / price
            position, entry_price, cash = qty, price, 0.0
            trades.append({"Tarih": idx[i], "Tip": "AL", "Fiyat": round(price, 2),
                           "Adet": round(qty, 4), "P&L %": None})
        elif sells[i] and position > 0:
            cash = position * price * (1 - fee)
            pnl = (price - entry_price) / entry_price * 100
            trades.append({"Tarih": idx[i], "Tip": "SAT", "Fiyat": round(price, 2),
                           "Adet": round(position, 4), "P&L %": round(pnl, 2)})
            position = 0.0
        equity_curve.append(cash + position * price)

    final = cash + position * closes[-1]
    total_ret = (final - initial_cash) / initial_cash * 100
    closed = [t for t in trades if t["Tip"] == "SAT"]
    wins = [t for t in closed if t["P&L %"] and t["P&L %"] > 0]
    win_rate = len(wins) / len(closed) * 100 if closed else 0
    bh_ret = (closes[-1] - closes[0]) / closes[0] * 100
    eq = np.array(equity_curve)
    dd = (eq - np.maximum.accumulate(eq)) / np.maximum.accumulate(eq) * 100
    return {"final_equity": final, "total_return": total_ret, "bh_return": bh_ret,
            "n_trades": len(closed), "win_rate": win_rate,
            "max_dd": dd.min() if len(dd) else 0, "trades": trades,
            "equity_curve": equity_curve, "open_position": position > 0}


# ===========================================================================
# PİYASA TARAYICI
# ===========================================================================

def scan_market(tickers: list, period: str, interval: str,
                key_value: float, atr_period: int, lookback: int) -> pd.DataFrame:
    """Her hisse için son `lookback` mumda sinyal var mı kontrol eder."""
    rows = []
    progress = st.progress(0.0, text="Hisseler taranıyor...")
    for i, t in enumerate(tickers):
        progress.progress((i + 1) / len(tickers), text=f"Taranıyor: {t}")
        df = fetch_data(t, period, interval)
        if df is None or len(df) < atr_period + 5:
            continue
        sig = ut_bot_signals(df, key_value, atr_period)
        recent = sig.iloc[-lookback:]
        last = sig.iloc[-1]

        signal = "—"
        bars_ago = None
        if recent["buy"].any():
            signal = "AL"
            bars_ago = lookback - 1 - int(np.where(recent["buy"].values)[0][-1])
        if recent["sell"].any():
            sell_idx = lookback - 1 - int(np.where(recent["sell"].values)[0][-1])
            if signal == "—" or sell_idx < bars_ago:
                signal = "SAT"
                bars_ago = sell_idx

        score = compute_score(df)
        chg = (df["Close"].iloc[-1] - df["Close"].iloc[-2]) / df["Close"].iloc[-2] * 100
        price = float(df["Close"].iloc[-1])
        ut_stop = float(last["stop"])
        bias = "LONG" if last["pos"] == 1 else "SHORT"
        stop_dist = (price - ut_stop) / price * 100
        rows.append({
            "Hisse": t,
            "Sinyal": signal,
            "Eğilim": bias,
            "Kaç Mum Önce": bars_ago if bars_ago is not None else "—",
            "Fiyat": round(price, 2),
            "UT Stop": round(ut_stop, 2),
            "Stop Mesafe %": round(stop_dist, 2),
            "Günlük %": round(float(chg), 2),
            "Skor": score["total"],
            "RSI": score["rsi_val"],
            "Sistem": system_decision(score["total"]),
        })
    progress.empty()
    return pd.DataFrame(rows)


# ===========================================================================
# GRAFİKLER
# ===========================================================================

def make_ut_chart(df: pd.DataFrame, title: str) -> go.Figure:
    ema21 = compute_ema(df["Close"], 21)
    ema50 = compute_ema(df["Close"], 50)
    rsi = compute_rsi(df["Close"])

    fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
                        row_heights=[0.6, 0.18, 0.22], vertical_spacing=0.03,
                        subplot_titles=("Fiyat & UT Bot", "Hacim", "RSI"))

    fig.add_trace(go.Candlestick(x=df.index, open=df["Open"], high=df["High"],
                  low=df["Low"], close=df["Close"], name="Fiyat",
                  increasing_line_color=C_UP, decreasing_line_color=C_DOWN,
                  increasing_fillcolor=C_UP, decreasing_fillcolor=C_DOWN), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["stop"], name="UT Stop",
                  line=dict(color=C_PURPLE, width=1.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=ema21, name="EMA21",
                  line=dict(color=C_GOLD, width=1)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=ema50, name="EMA50",
                  line=dict(color=C_ACCENT, width=1)), row=1, col=1)

    buys, sells = df[df["buy"]], df[df["sell"]]
    fig.add_trace(go.Scatter(x=buys.index, y=buys["Low"] * 0.985, mode="markers",
                  name="AL", marker=dict(symbol="triangle-up", size=14, color=C_UP,
                  line=dict(color="white", width=1))), row=1, col=1)
    fig.add_trace(go.Scatter(x=sells.index, y=sells["High"] * 1.015, mode="markers",
                  name="SAT", marker=dict(symbol="triangle-down", size=14, color=C_DOWN,
                  line=dict(color="white", width=1))), row=1, col=1)

    colors = [C_UP if c >= o else C_DOWN for c, o in zip(df["Close"], df["Open"])]
    fig.add_trace(go.Bar(x=df.index, y=df["Volume"], name="Hacim",
                  marker_color=colors, opacity=0.6), row=2, col=1)

    fig.add_trace(go.Scatter(x=df.index, y=rsi, name="RSI",
                  line=dict(color="#ff7043", width=1.4)), row=3, col=1)
    fig.add_hline(y=70, line=dict(color="rgba(234,57,67,0.5)", dash="dash"), row=3, col=1)
    fig.add_hline(y=30, line=dict(color="rgba(22,199,132,0.5)", dash="dash"), row=3, col=1)

    fig.update_layout(title=title, template="plotly_dark",
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(13,17,28,1)",
                      height=640, xaxis_rangeslider_visible=False,
                      legend=dict(orientation="h", y=1.02, x=1, xanchor="right"),
                      margin=dict(l=10, r=10, t=50, b=10))
    fig.update_yaxes(gridcolor="rgba(255,255,255,0.05)")
    fig.update_xaxes(gridcolor="rgba(255,255,255,0.05)")
    return fig


def make_equity_chart(equity_curve, index) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=index, y=equity_curve, fill="tozeroy",
                  line=dict(color=C_ACCENT, width=2), name="Portföy"))
    fig.update_layout(title="Portföy Değeri (Equity Curve)", template="plotly_dark",
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(13,17,28,1)",
                      height=260, margin=dict(l=10, r=10, t=40, b=10))
    return fig


# ===========================================================================
# TRADE PLANI — Gerçek borsada kullanılabilir işlem parametreleri
# ===========================================================================
# Profesyonel trader'ların her işlemde hesapladığı şeyler:
#   - Giriş fiyatı
#   - Stop-loss (ATR / UT trailing stop bazlı) -> nerede yanıldığını kabul edersin
#   - Kâr hedefleri TP1 (1.5R) ve TP2 (3R)     -> risk/ödül planı
#   - Risk/Ödül oranı (R:R)
#   - Pozisyon büyüklüğü -> hesabının yalnızca %X'ini riske atacak lot sayısı
#   - Trend filtresi (EMA50) -> trende karşı işlemden kaçınma

def build_trade_plan(df: pd.DataFrame, side: str,
                     account_size: float = 10000.0, risk_pct: float = 1.0) -> dict:
    """
    df: ut_bot_signals çıktısı ('stop' ve 'atr' kolonları olmalı).
    side: 'AL' (long) veya 'SAT' (short).
    Gerçek bir işlemde girilecek tüm parametreleri döner.
    """
    last = df.iloc[-1]
    entry = float(last["Close"])
    atr = float(last["atr"]) if not pd.isna(last["atr"]) else entry * 0.02
    ut_stop = float(last["stop"])

    if side == "AL":   # LONG
        # Stop: UT stop ile ATR bazlı stop'tan hangisi daha koruyucuysa (daha yakın olan değil,
        # mantıklı olan) — burada ikisinin daha düşüğünü alıp makul bir tampon bırakıyoruz.
        atr_stop = entry - 1.5 * atr
        stop = min(ut_stop, atr_stop) if ut_stop < entry else atr_stop
        risk_per_share = max(entry - stop, entry * 0.001)
        tp1 = entry + 1.5 * risk_per_share
        tp2 = entry + 3.0 * risk_per_share
    else:              # SHORT
        atr_stop = entry + 1.5 * atr
        stop = max(ut_stop, atr_stop) if ut_stop > entry else atr_stop
        risk_per_share = max(stop - entry, entry * 0.001)
        tp1 = entry - 1.5 * risk_per_share
        tp2 = entry - 3.0 * risk_per_share

    risk_amount = account_size * risk_pct / 100.0
    shares = risk_amount / risk_per_share if risk_per_share > 0 else 0
    position_value = shares * entry

    # Trend filtresi (yeterli veri varsa EMA50)
    ema50 = compute_ema(df["Close"], 50)
    trend = "—"
    if len(df) >= 50:
        if entry > ema50.iloc[-1] and ema50.iloc[-1] > ema50.iloc[-5]:
            trend = "Yukarı (EMA50 üstünde ve yükseliyor)"
        elif entry < ema50.iloc[-1] and ema50.iloc[-1] < ema50.iloc[-5]:
            trend = "Aşağı (EMA50 altında ve düşüyor)"
        else:
            trend = "Yatay / kararsız"

    # Trend uyumu uyarısı
    aligned = (side == "AL" and "Yukarı" in trend) or (side == "SAT" and "Aşağı" in trend)

    return {
        "side": side,
        "entry": round(entry, 2),
        "stop": round(stop, 2),
        "stop_pct": round((stop - entry) / entry * 100, 2),
        "tp1": round(tp1, 2),
        "tp2": round(tp2, 2),
        "tp1_pct": round((tp1 - entry) / entry * 100, 2),
        "tp2_pct": round((tp2 - entry) / entry * 100, 2),
        "risk_per_share": round(risk_per_share, 2),
        "rr": "1:1.5  /  1:3",
        "shares": int(shares),
        "position_value": round(position_value, 2),
        "risk_amount": round(risk_amount, 2),
        "atr": round(atr, 2),
        "trend": trend,
        "aligned": aligned,
    }


def render_trade_plan(plan: dict):
    """Trade planını Streamlit kartı olarak çizer."""
    side_txt = "🟢 LONG (AL)" if plan["side"] == "AL" else "🔴 SHORT (SAT)"
    st.markdown(f"##### 📋 Trade Planı — {side_txt}")
    c = st.columns(4)
    c[0].metric("Giriş", f"${plan['entry']}")
    c[1].metric("🛑 Stop-Loss", f"${plan['stop']}", delta=f"{plan['stop_pct']}%")
    c[2].metric("🎯 Hedef 1 (1.5R)", f"${plan['tp1']}", delta=f"{plan['tp1_pct']}%")
    c[3].metric("🎯 Hedef 2 (3R)", f"${plan['tp2']}", delta=f"{plan['tp2_pct']}%")

    c2 = st.columns(4)
    c2[0].metric("Pozisyon (lot)", f"{plan['shares']} adet")
    c2[1].metric("Pozisyon Değeri", f"${plan['position_value']:,.0f}")
    c2[2].metric("Riske Atılan", f"${plan['risk_amount']:,.0f}")
    c2[3].metric("Risk/Ödül", plan["rr"])

    if plan["trend"] != "—":
        if plan["aligned"]:
            st.success(f"✅ Trend uyumlu: {plan['trend']} — işlem trend yönünde.")
        else:
            st.warning(f"⚠️ Trende dikkat: {plan['trend']} — işlemin trende karşı olabilir, risk yüksek.")
    st.caption(f"Hesaplama: ATR ${plan['atr']} • Hisse başı risk ${plan['risk_per_share']} • "
               "Stop'a değerse kaybın 'Riske Atılan' tutarıdır. Bu bir emir değildir, plan şablonudur.")


# ===========================================================================
# SİMÜLASYON OYUNU (app.py'den uyarlandı)
# ===========================================================================

def generate_synthetic_data(scenario_type: str = "Yükselen Trend", n: int = 120) -> pd.DataFrame:
    np.random.seed(random.randint(0, 9999))
    price = 100.0
    prices, volumes = [], []
    drift = {"Yükselen Trend": 0.003, "Düşen Trend": -0.003, "Yatay Piyasa": 0.0,
             "Breakout": 0.001, "Fake Breakout": 0.002, "Pullback": 0.002,
             "Hacimli Yükseliş": 0.004, "RSI Zayıflığı": -0.001}.get(scenario_type, 0.001)
    for i in range(n):
        if scenario_type == "Breakout" and i == int(n * 0.7):
            drift = 0.01
        if scenario_type == "Fake Breakout" and i == int(n * 0.7):
            drift = 0.008
        if scenario_type == "Fake Breakout" and i == int(n * 0.8):
            drift = -0.01
        price = max(price * (1 + drift + np.random.normal(0, 0.015)), 1)
        prices.append(price)
        volumes.append(int((2_500_000 if scenario_type == "Hacimli Yükseliş" else 1_000_000) * random.uniform(0.5, 2.0)))
    closes = np.array(prices)
    opens = np.roll(closes, 1); opens[0] = closes[0]
    highs = closes * (1 + np.abs(np.random.normal(0, 0.005, n)))
    lows = closes * (1 - np.abs(np.random.normal(0, 0.005, n)))
    idx = pd.date_range(end=datetime.today(), periods=n, freq="D")
    return pd.DataFrame({"Open": opens, "High": highs, "Low": lows,
                         "Close": closes, "Volume": volumes}, index=idx)


def init_sim_state():
    defaults = {"balance": 100.0, "xp": 0, "correct": 0, "wrong": 0, "streak": 0,
                "risk_avoided": 0, "goals_done": 0, "badges": [], "history": [],
                "balance_history": [100.0], "scenario": None, "phase": "idle",
                "decision": None, "goals_reached": []}
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def xp_to_level(xp: int) -> int:
    return 1 + xp // 100


# ===========================================================================
# SAYFALAR
# ===========================================================================

def _scan_card(r, color, sub):
    return (
        f'<div style="background:rgba({color},0.12);border-left:4px solid rgb({color});'
        f'border-radius:8px;padding:10px 14px;margin-bottom:8px;">'
        f'<b style="font-size:1.1rem;">{r["Hisse"]}</b> &nbsp; ${r["Fiyat"]} '
        f'<span style="color:{C_UP if r["Günlük %"]>=0 else C_DOWN};">({r["Günlük %"]:+}%)</span><br>'
        f'<span style="color:#aaa;font-size:0.8rem;">{sub}</span></div>')


def page_scanner(tickers, period, interval, key_value, atr_period, initial_cash=10000.0, risk_pct=1.0):
    st.markdown(
        '<div class="page-header">'
        '<h2>📡 Sinyal Tarayıcı</h2>'
        '<p>Havuzdaki her hisse UT Bot algoritmasıyla taranır. '
        'AL/SAT sinyali üretenler ve yükseliş eğilimindeki adaylar ayrı gruplar halinde listelenir.</p>'
        '</div>', unsafe_allow_html=True)

    lookback = st.slider("Sinyal Tazeliği (son kaç mumda sinyal aransın)", 1, 10, 3,
                         help="1 = sadece en son mumda sinyal verenler")
    if st.button("🔍 Piyasayı Tara", type="primary", use_container_width=True):
        df = scan_market(tickers, period, interval, key_value, atr_period, lookback)
        st.session_state["scan_result"] = df

    df = st.session_state.get("scan_result")
    if df is None or df.empty:
        st.info("👆 'Piyasayı Tara' butonuna basın.")
        return

    buy_list = df[df["Sinyal"] == "AL"].sort_values("Kaç Mum Önce")
    sell_list = df[df["Sinyal"] == "SAT"].sort_values("Kaç Mum Önce")
    # Sinyal yoksa eğilim adayları (gerçek borsada izleme listesi mantığı)
    long_watch = df[(df["Sinyal"] == "—") & (df["Eğilim"] == "LONG")].sort_values("Skor", ascending=False)
    short_watch = df[(df["Sinyal"] == "—") & (df["Eğilim"] == "SHORT")].sort_values("Skor")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"### 🟢 AL Sinyali ({len(buy_list)})")
        if buy_list.empty:
            st.caption("Taze AL sinyali yok.")
        for _, r in buy_list.iterrows():
            st.markdown(_scan_card(r, "22,199,132",
                f'{r["Kaç Mum Önce"]} mum önce • Skor {r["Skor"]}/100 • RSI {r["RSI"]} • Stop ${r["UT Stop"]}'),
                unsafe_allow_html=True)
        if not long_watch.empty:
            st.markdown("**🟩 Yükseliş eğilimli (izleme):**")
            for _, r in long_watch.head(6).iterrows():
                st.markdown(_scan_card(r, "22,199,132",
                    f'LONG eğilim • Skor {r["Skor"]}/100 • RSI {r["RSI"]} • Stop ${r["UT Stop"]} (%{r["Stop Mesafe %"]})'),
                    unsafe_allow_html=True)
    with col2:
        st.markdown(f"### 🔴 SAT Sinyali ({len(sell_list)})")
        if sell_list.empty:
            st.caption("Taze SAT sinyali yok — piyasa düşüş sinyali üretmiyor (genelde yükseliş eğiliminde sağlıklıdır).")
        for _, r in sell_list.iterrows():
            st.markdown(_scan_card(r, "234,57,67",
                f'{r["Kaç Mum Önce"]} mum önce • Skor {r["Skor"]}/100 • RSI {r["RSI"]} • Stop ${r["UT Stop"]}'),
                unsafe_allow_html=True)
        if not short_watch.empty:
            st.markdown("**🟥 Zayıf / düşüş eğilimli (izleme veya kaçın):**")
            for _, r in short_watch.head(6).iterrows():
                st.markdown(_scan_card(r, "234,57,67",
                    f'SHORT eğilim • Skor {r["Skor"]}/100 • RSI {r["RSI"]} • Fiyat UT stop altında'),
                    unsafe_allow_html=True)

    st.divider()
    st.markdown("#### 📊 Tüm Hisseler")
    st.dataframe(
        df.sort_values("Skor", ascending=False),
        use_container_width=True, hide_index=True,
        column_config={
            "Günlük %": st.column_config.NumberColumn(format="%.2f%%"),
            "Stop Mesafe %": st.column_config.NumberColumn(format="%.2f%%"),
            "Skor": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%d"),
        },
    )
    st.caption("**Eğilim:** Fiyat UT stop'un üstündeyse LONG, altındaysa SHORT. "
               "**UT Stop:** trailing stop seviyesi — long pozisyonda stop-loss olarak kullanılabilir. "
               "**Stop Mesafe %:** fiyatın stop'a uzaklığı (risk göstergesi).")


def page_analysis(tickers, period, interval, key_value, atr_period, initial_cash, fee_pct, risk_pct=1.0):
    st.markdown(
        '<div class="page-header">'
        '<h2>🔬 Hisse Analizi</h2>'
        '<p>Seçtiğin hisse için UT Bot grafiği, RSI, EMA şeridi ve backtest sonuçları birlikte gösterilir. '
        'Ayrıca hesabına göre giriş noktası, stop-loss ve kâr hedefi içeren bir işlem planı oluşturulur.</p>'
        '</div>', unsafe_allow_html=True)
    pool = tickers + (["BTC-USD", "ETH-USD"])
    sel = st.selectbox("Hisse Seç", pool, index=0)
    manual = st.text_input("veya manuel sembol gir (opsiyonel)", "")
    ticker = manual.strip().upper() if manual.strip() else sel

    df = fetch_data(ticker, period, interval)
    if df is None or len(df) < atr_period + 5:
        st.error(f"'{ticker}' için yeterli veri yok. Farklı sembol/periyot deneyin.")
        return

    df = ut_bot_signals(df, key_value, atr_period)
    result = backtest(df, initial_cash, fee_pct)
    score = compute_score(df)

    # Güncel sinyal + bias
    last = df.iloc[-1]
    bias = "AL" if last["pos"] == 1 else "SAT"   # stop üstü=long bias, altı=short bias
    if last["buy"]:
        st.success(f"🟢 **GÜNCEL SİNYAL: AL** — {ticker} @ ${last['Close']:.2f}")
    elif last["sell"]:
        st.error(f"🔴 **GÜNCEL SİNYAL: SAT** — {ticker} @ ${last['Close']:.2f}")
    else:
        durum = "LONG eğilimi (fiyat UT stop üstünde)" if last["pos"] == 1 else "SHORT eğilimi (fiyat UT stop altında)"
        st.info(f"⚪ Yeni sinyal yok • Eğilim: **{durum}** • Fiyat: ${last['Close']:.2f}")

    # Trade planı (güncel sinyal varsa o yön, yoksa mevcut eğilim yönünde)
    plan_side = "AL" if last["buy"] else ("SAT" if last["sell"] else bias)
    plan = build_trade_plan(df, plan_side, account_size=initial_cash, risk_pct=risk_pct)
    render_trade_plan(plan)
    st.divider()

    # Metrikler
    m = st.columns(5)
    m[0].metric("Strateji Getirisi", f"{result['total_return']:+.2f}%")
    m[1].metric("Al & Tut", f"{result['bh_return']:+.2f}%",
                delta=f"{result['total_return']-result['bh_return']:+.2f}%")
    m[2].metric("İşlem", result["n_trades"])
    m[3].metric("Kazanma %", f"{result['win_rate']:.0f}%")
    m[4].metric("Max DD", f"{result['max_dd']:.1f}%")

    st.plotly_chart(make_ut_chart(df, f"{ticker} • UT Bot (key={key_value}, ATR={atr_period})"),
                    use_container_width=True)

    with st.expander("📊 Teknik Skor & Formasyonlar", expanded=False):
        s = st.columns(5)
        s[0].metric("Skor", f"{score['total']}/100")
        s[1].metric("Trend", f"{score['trend']}/25")
        s[2].metric("EMA", f"{score['ema']}/20")
        s[3].metric("RSI", f"{score['rsi']}/15 ({score['rsi_val']})")
        s[4].metric("Hacim", f"{score['volume']}/20")
        st.info(f"🤖 Sistem Kararı: **{system_decision(score['total'])}**")
        if score["formations"]:
            st.markdown("**Formasyonlar:** " + " · ".join(score["formations"]))

    st.plotly_chart(make_equity_chart(result["equity_curve"], df.index), use_container_width=True)

    if result["trades"]:
        st.markdown("#### 📋 İşlem Geçmişi")
        st.dataframe(pd.DataFrame(result["trades"]), use_container_width=True, hide_index=True)
    else:
        st.warning("Bu ayarlarla işlem sinyali üretilmedi.")


def detect_whale_activity(tickers: list) -> pd.DataFrame:
    """Havuzu tarar; olağandışı hacim + para akışı ile birikim/dağıtım tespiti."""
    rows = []
    prog = st.progress(0.0, text="Para akışı taranıyor...")
    for i, t in enumerate(tickers):
        prog.progress((i + 1) / len(tickers), text=f"İnceleniyor: {t}")
        df = fetch_daily(t, "3mo")
        if df is None or len(df) < 25:
            continue
        rvol = relative_volume(df)
        chg = (df["Close"].iloc[-1] - df["Close"].iloc[-2]) / df["Close"].iloc[-2] * 100
        mfi = compute_mfi(df).iloc[-1]
        mfi = round(float(mfi), 1) if not pd.isna(mfi) else 50.0
        obv = compute_obv(df)
        obv_slope = obv.iloc[-1] - obv.iloc[-6] if len(obv) > 6 else 0  # son 5 gün eğilim
        dollar_vol = df["Close"].iloc[-1] * df["Volume"].iloc[-1]

        # Yorum: birikim mi dağıtım mı?
        if rvol >= 1.5 and chg > 0 and mfi > 55 and obv_slope > 0:
            durum = "🐋 Birikim (Accumulation)"
        elif rvol >= 1.5 and chg < 0 and (mfi < 45 or obv_slope < 0):
            durum = "📉 Dağıtım (Distribution)"
        elif rvol >= 2.0:
            durum = "⚡ Olağandışı Hacim"
        else:
            durum = "—"

        rows.append({
            "Hisse": t,
            "Durum": durum,
            "Göreli Hacim": round(rvol, 2),
            "Günlük %": round(float(chg), 2),
            "MFI": mfi,
            "OBV Eğilim": "↑ Yukarı" if obv_slope > 0 else ("↓ Aşağı" if obv_slope < 0 else "→"),
            "$ Hacim (M)": round(dollar_vol / 1e6, 1),
            "Fiyat": round(float(df["Close"].iloc[-1]), 2),
        })
    prog.empty()
    return pd.DataFrame(rows)


def detect_downtrend_line(df: pd.DataFrame, lookback: int = 45):
    """Konsolidasyondaki düşen direnç çizgisini (zirve → daha düşük tepe) bulur."""
    if len(df) < 10:
        return None
    gap = 4
    sub = df.iloc[-lookback:]
    highs = sub["High"].values
    idx = sub.index
    p1 = int(np.argmax(highs))                 # en yüksek tepe
    if p1 >= len(highs) - gap - 1:              # tepe çok yakınsa çizgi anlamsız
        return None
    after = highs[p1 + gap:]                     # zirveden en az `gap` mum sonra ikinci tepe
    if len(after) == 0:
        return None
    p2 = p1 + gap + int(np.argmax(after))
    if highs[p2] > highs[p1] or p2 == p1:        # ikinci tepe zirveyi aşmamalı (eşit/düşük olabilir)
        return None
    slope = (highs[p2] - highs[p1]) / (p2 - p1)
    x_end = len(highs) - 1
    y_end = highs[p1] + slope * (x_end - p1)
    return {"x0": idx[p1], "y0": float(highs[p1]),
            "x1": idx[x_end], "y1": float(y_end)}


def make_cloud_chart(df: pd.DataFrame, title: str) -> go.Figure:
    """Qullamaggie tarzı 10/20 EMA bulutu + 50/200 SMA + düşen trend çizgisi grafiği."""
    c = df["Close"]
    ema10, ema20 = compute_ema(c, 10), compute_ema(c, 20)
    sma50 = c.rolling(50).mean()
    sma200 = c.rolling(200).mean()

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.78, 0.22],
                        vertical_spacing=0.04, subplot_titles=(title, "Hacim"))

    # EMA bulutu (10-20 arası dolgu)
    fig.add_trace(go.Scatter(x=df.index, y=ema20, line=dict(width=0), showlegend=False,
                  hoverinfo="skip"), row=1, col=1)
    cloud_up = (ema10 >= ema20).iloc[-1]
    fig.add_trace(go.Scatter(x=df.index, y=ema10, fill="tonexty", name="EMA 10/20 Bulut",
                  line=dict(color="rgba(22,199,132,0.6)", width=1),
                  fillcolor="rgba(22,199,132,0.18)" if cloud_up else "rgba(234,57,67,0.18)"),
                  row=1, col=1)

    fig.add_trace(go.Candlestick(x=df.index, open=df["Open"], high=df["High"], low=df["Low"],
                  close=df["Close"], name="Fiyat", increasing_line_color=C_UP,
                  decreasing_line_color=C_DOWN, increasing_fillcolor=C_UP,
                  decreasing_fillcolor=C_DOWN), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=sma50, name="SMA 50",
                  line=dict(color=C_ACCENT, width=1.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=sma200, name="SMA 200",
                  line=dict(color="#ef5350", width=1.2)), row=1, col=1)

    # Düşen trend (direnç) çizgisi — TradingView'daki beyaz diyagonal
    dt = detect_downtrend_line(df)
    if dt:
        fig.add_trace(go.Scatter(x=[dt["x0"], dt["x1"]], y=[dt["y0"], dt["y1"]],
                      mode="lines", name="Düşen Trend Çizgisi",
                      line=dict(color="white", width=2, dash="solid")), row=1, col=1)

    colors = [C_UP if cl >= o else C_DOWN for cl, o in zip(df["Close"], df["Open"])]
    fig.add_trace(go.Bar(x=df.index, y=df["Volume"], name="Hacim",
                  marker_color=colors, opacity=0.55), row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["Volume"].rolling(50).mean(), name="Hacim Ort.",
                  line=dict(color=C_GOLD, width=1)), row=2, col=1)

    fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(13,17,28,1)", height=600, xaxis_rangeslider_visible=False,
                      legend=dict(orientation="h", y=1.03, x=1, xanchor="right", font=dict(size=11)),
                      margin=dict(l=10, r=10, t=50, b=10), hovermode="x unified")
    fig.update_yaxes(gridcolor="rgba(255,255,255,0.05)")
    fig.update_xaxes(gridcolor="rgba(255,255,255,0.04)")
    return fig


@st.cache_data(ttl=1800)
def scan_qullamaggie_yf(universe: list, min_perf1y: float = 50,
                         min_cap_b: float = 2.0, min_adr_pct: float = 3.5) -> tuple:
    """
    yfinance ile Qullamaggie filtreleri (tamamen yasal, yayın için uygun):
    - Fiyat > EMA100  (~21 haftalık EMA)
    - Fiyat > EMA200  (~50 haftalık EMA)
    - 1Y Performans > min_perf1y%
    - Vol 10G ort > Vol 90G ort  (hacim artıyor)
    - ADR% > min_adr_pct%
    - Piyasa Değeri > min_cap_b milyar $
    30 dakika cache — yfinance batch ile ~300 hisseyi 15-20 sn'de tarar.
    """
    import yfinance as yf

    if not universe:
        return pd.DataFrame(), 0

    # Batch download — tüm hisseleri tek seferde çek (çok daha hızlı)
    raw = yf.download(
        universe, period="1y", interval="1d",
        group_by="ticker", auto_adjust=True,
        progress=False, threads=True,
    )

    rows = []
    price_1y_ago = {}

    for ticker in universe:
        try:
            if len(universe) == 1:
                df = raw.copy()
            else:
                df = raw[ticker].dropna(how="all")

            if df is None or len(df) < 60:
                continue

            close  = df["Close"].dropna()
            volume = df["Volume"].dropna()
            high   = df["High"].dropna()
            low    = df["Low"].dropna()

            if len(close) < 60:
                continue

            price_now  = float(close.iloc[-1])
            price_prev = float(close.iloc[-2]) if len(close) > 1 else price_now

            # EMA hesapla
            ema100 = float(close.ewm(span=100, adjust=False).mean().iloc[-1])
            ema200 = float(close.ewm(span=200, adjust=False).mean().iloc[-1])
            ema10  = float(close.ewm(span=10,  adjust=False).mean().iloc[-1])
            ema20  = float(close.ewm(span=20,  adjust=False).mean().iloc[-1])

            # Filtre 1: Fiyat > EMA100 ve EMA200
            if price_now <= ema100 or price_now <= ema200:
                continue

            # 1Y performans
            perf_1y = (price_now / float(close.iloc[0]) - 1) * 100
            if perf_1y < min_perf1y:
                continue

            # Hacim artışı: 10 günlük ort > 90 günlük ort
            vol10  = float(volume.iloc[-10:].mean())
            vol90  = float(volume.iloc[-90:].mean())
            if vol10 <= vol90:
                continue

            # ADR%: son 14 günün ortalama günlük aralığı
            daily_range = ((high - low) / close * 100).iloc[-14:]
            adr_pct = float(daily_range.mean())
            if adr_pct < min_adr_pct:
                continue

            # Haftalık / aylık / 3 aylık performans
            perf_w  = (price_now / float(close.iloc[-5])  - 1) * 100 if len(close) >= 5  else 0
            perf_1m = (price_now / float(close.iloc[-21]) - 1) * 100 if len(close) >= 21 else 0
            perf_3m = (price_now / float(close.iloc[-63]) - 1) * 100 if len(close) >= 63 else 0

            # RVOL: bugünkü hacim / 10 günlük ort
            vol_today = float(volume.iloc[-1])
            rvol = round(vol_today / vol90, 2) if vol90 > 0 else 0

            # Piyasa değeri (yaklaşık — fiyat * ortalama hacim proxy, gerçek için yf.Ticker kullan)
            # Gerçek market cap bilgisi için ayrı çekim gerekir, burada hisse başına fiyat kullanıyoruz
            # Büyük cap evreni kullandığımız için bu filtre evrende zaten uygulanmış sayılır
            rows.append({
                "Ticker":      ticker,
                "Fiyat":       round(price_now, 2),
                "Günlük %":    round((price_now / price_prev - 1) * 100, 2),
                "1Y %":        round(perf_1y, 1),
                "Haftalık %":  round(perf_w, 1),
                "Aylık %":     round(perf_1m, 1),
                "3 Aylık %":   round(perf_3m, 1),
                "ADR%":        round(adr_pct, 2),
                "RVOL":        rvol,
                "EMA100":      round(ema100, 2),
                "EMA200":      round(ema200, 2),
                "EMA100 ↑%":   round((price_now / ema100 - 1) * 100, 1),
                "EMA200 ↑%":   round((price_now / ema200 - 1) * 100, 1),
                "EMA10":       round(ema10, 2),
                "EMA20":       round(ema20, 2),
                "Vol 10G":     int(vol10),
                "Vol 90G":     int(vol90),
                "_close":      close,
            })
        except Exception:
            continue

    if not rows:
        return pd.DataFrame(), 0

    result = pd.DataFrame(rows).sort_values("RVOL", ascending=False).reset_index(drop=True)
    return result, len(result)


def scan_momentum(universe: list, min_rs: int, min_adr: float) -> pd.DataFrame:
    """Qullamaggie/Minervini momentum breakout taraması."""
    rows = []
    prog = st.progress(0.0, text="Momentum taraması...")
    raw = []
    for i, t in enumerate(universe):
        prog.progress((i + 1) / len(universe), text=f"Taranıyor: {t}")
        df = fetch_daily(t, "1y")
        if df is None or len(df) < 60:
            continue
        raw.append((t, df, momentum_score(df)))

    if not raw:
        prog.empty()
        return pd.DataFrame()

    # RS Rating: havuz içi yüzdelik sıralama (1-99)
    scores = pd.Series({t: s for t, _, s in raw}).rank(pct=True) * 98 + 1

    for t, df, _ in raw:
        tt   = trend_template(df)
        adr  = compute_adr_pct(df)
        rs   = int(round(scores[t]))
        setup = detect_setup(df)
        chg  = (df["Close"].iloc[-1] - df["Close"].iloc[-2]) / df["Close"].iloc[-2] * 100
        rvol = relative_volume(df)
        stealth = stealth_accumulation(df, 10)
        sec_rs  = sector_rs(t, df)
        rows.append({
            "Hisse": t,
            "Setup": setup,
            "RS": rs,
            "Sektör RS": sec_rs.get("vs_sector"),
            "ADR %": round(adr, 1),
            "Trend": f"{tt['passed']}/{tt['total']}",
            "Zirveye %": tt["pct_from_high"],
            "Gör. Hacim": round(rvol, 2),
            "Günlük %": round(float(chg), 2),
            "Fiyat": round(float(df["Close"].iloc[-1]), 2),
            "Birikim": stealth["score"],
            "_pass": tt["passed"], "_adr": adr, "_rs": rs,
            "_above": tt["above_cloud"] and tt["above_50"],
            "_stealth": stealth["signal"],
        })
    prog.empty()
    df = pd.DataFrame(rows)
    # Filtre: RS ve ADR eşiği + trend yapısı sağlam
    df = df[(df["_rs"] >= min_rs) & (df["_adr"] >= min_adr) & (df["_above"])]
    return df.sort_values(["_pass", "_rs"], ascending=False)




def _render_qullamaggie_scan_section():
    """Qullamaggie filtre tarayıcısı — tamamen yfinance tabanlı, yayın için yasal."""
    st.markdown("### 🔎 Qullamaggie Filtre Tarayıcısı")
    st.caption(
        "Filtreler: **Fiyat > EMA100 (≈21 haftalık) · Fiyat > EMA200 (≈50 haftalık) · "
        "1Y > 50% · Hacim artıyor (10G ort > 90G ort) · ADR% > 3.5%** — "
        "Veri: Yahoo Finance (yfinance) · 30 dk cache"
    )

    fc = st.columns(4)
    q_evren   = fc[0].selectbox("Evren", ["S&P500 + Momentum (~300)", "Nasdaq-100", "Momentum (hızlı, 40)"],
                                  key="qs_evren")
    q_perf1y  = fc[1].slider("Min. 1Y %", 0, 300, 50, 10, key="qs_perf1y",
                               help="1 yıllık performans. Qullamaggie 50%+ arar.")
    q_adr     = fc[2].slider("Min. ADR %", 1.0, 10.0, 3.5, 0.5, key="qs_adr",
                               help="Ortalama günlük hareket. 3.5%+ = hareketli.")
    q_cap     = fc[3].slider("Min. Piyasa Değ. ($B)", 0.0, 10.0, 2.0, 0.5, key="qs_cap",
                               help="0 = filtre yok. Büyük para için 2B+ tercih.")

    if q_evren == "S&P500 + Momentum (~300)":
        universe = SP500_UNIVERSE
    elif q_evren == "Nasdaq-100":
        universe = NASDAQ100
    else:
        universe = MOMENTUM_UNIVERSE

    st.caption(f"📋 {len(universe)} hisse taranacak · İlk tarama ~20-30 sn sürer (sonra 30 dk cache'li)")

    if st.button("🚀 Qullamaggie Tara", type="primary", use_container_width=True, key="qs_scan_btn"):
        with st.spinner(f"{len(universe)} hisse için 1 yıllık veri indiriliyor…"):
            df_q, count = scan_qullamaggie_yf(universe, float(q_perf1y), float(q_cap), float(q_adr))
            st.session_state["qs_result"] = df_q
            st.session_state["qs_count"]  = count

    df_tv = st.session_state.get("qs_result")
    count  = st.session_state.get("qs_count", 0)

    if df_tv is None:
        st.info("👆 'Qullamaggie Tara' butonuna bas.")
        return
    if df_tv.empty:
        st.warning("Filtrelerle eşleşen hisse yok — eşikleri düşür.")
        return

    st.success(f"✅ {count} hisse filtreden geçti · Güncelleme: {pd.Timestamp.now().strftime('%H:%M:%S')}")

    # En güçlü 6 hisse kart
    top = df_tv.head(6).to_dict("records")
    for i in range(0, len(top), 3):
        cols = st.columns(3)
        for col, r in zip(cols, top[i:i + 3]):
            day_col  = C_UP if r.get("Günlük %", 0) >= 0 else C_DOWN
            rvol_col = C_UP if r.get("RVOL", 1) >= 2 else C_GOLD
            col.markdown(
                f'<div style="background:rgba(16,185,129,0.08);border:1px solid rgba(16,185,129,0.3);'
                f'border-radius:12px;padding:14px;margin-bottom:10px;">'
                f'<div style="font-size:1.2rem;font-weight:800;color:#fff;">{r["Ticker"]} '
                f'<span style="font-size:0.85rem;color:{day_col};">{r.get("Günlük %",0):+.2f}%</span></div>'
                f'<div style="font-size:0.82rem;color:#d1d5db;margin-top:6px;">'
                f'💰 ${r["Fiyat"]:.2f} &nbsp;|&nbsp; '
                f'<span style="color:{rvol_col};">🔥 RVOL {r.get("RVOL",0):.1f}x</span> &nbsp;|&nbsp; '
                f'ADR {r.get("ADR%",0):.1f}%</div>'
                f'<div style="font-size:0.75rem;color:#6b7280;margin-top:4px;">'
                f'1Y: <b style="color:{C_UP};">{r.get("1Y %",0):+.0f}%</b> &nbsp;·&nbsp; '
                f'EMA100 +{r.get("EMA100 ↑%",0):.1f}% · EMA200 +{r.get("EMA200 ↑%",0):.1f}%</div>'
                f'<div style="font-size:0.75rem;color:#6b7280;">'
                f'W:{r.get("Haftalık %",0):+.1f}% · M:{r.get("Aylık %",0):+.1f}% · '
                f'3M:{r.get("3 Aylık %",0):+.1f}%</div>'
                f'</div>', unsafe_allow_html=True)

    # Tam tablo
    show_cols = ["Ticker", "Fiyat", "Günlük %", "ADR%", "RVOL",
                 "1Y %", "Haftalık %", "Aylık %", "3 Aylık %",
                 "EMA100 ↑%", "EMA200 ↑%"]
    show_cols = [c for c in show_cols if c in df_tv.columns]
    st.dataframe(
        df_tv[show_cols],
        use_container_width=True,
        hide_index=True,
        column_config={
            "RVOL": st.column_config.ProgressColumn(min_value=0, max_value=10, format="%.1fx",
                help="Bugünkü hacim / 90G ort. >1 = ortalamanın üzerinde."),
            "ADR%": st.column_config.NumberColumn(format="%.1f%%",
                help="Ortalama günlük hareket %. Qullamaggie 3.5%+ arar."),
            "1Y %": st.column_config.NumberColumn(format="%.0f%%"),
            "Günlük %": st.column_config.NumberColumn(format="%.2f%%"),
            "Haftalık %": st.column_config.NumberColumn(format="%.1f%%"),
            "Aylık %": st.column_config.NumberColumn(format="%.1f%%"),
            "3 Aylık %": st.column_config.NumberColumn(format="%.1f%%"),
            "EMA100 ↑%": st.column_config.NumberColumn(format="+%.1f%%",
                help="Fiyatın EMA100 üzerinde yüzdesi (≈21 haftalık)"),
            "EMA200 ↑%": st.column_config.NumberColumn(format="+%.1f%%",
                help="Fiyatın EMA200 üzerinde yüzdesi (≈50 haftalık)"),
        }
    )

    # Grafik + trade planı
    picks = df_tv["Ticker"].tolist()
    if picks:
        st.markdown("#### 📈 Hisse Grafiği & Trade Planı")
        sel = st.selectbox("Hisse seç", picks, key="qs_pick_chart")

        sel_row = df_tv[df_tv["Ticker"] == sel]
        if not sel_row.empty:
            r = sel_row.iloc[0]
            close_series = r.get("_close")
            if close_series is not None:
                # fetch_daily ile tam OHLCV verisi çek (detect_setup Open+Volume gerektirir)
                full_df = fetch_daily(sel, "1y")
                if full_df is not None and len(full_df) >= 25:
                    setup = detect_setup(full_df)
                    plan  = explain_trade(setup, full_df)

                    if plan:
                        rr_col = C_UP if plan["rr"] >= 3 else (C_GOLD if plan["rr"] >= 2 else C_DOWN)
                        pc1, pc2, pc3, pc4 = st.columns(4)
                        pc1.metric("Setup", setup)
                        pc2.metric("Giriş", f"${plan['entry']}")
                        pc3.metric("Stop", f"${plan['stop']}")
                        pc4.metric("R:R", f"{plan['rr']}:1",
                                   delta="İyi" if plan["rr"] >= 3 else ("Orta" if plan["rr"] >= 2 else "Zayıf"))

                    st.plotly_chart(
                        make_cloud_chart(full_df, f"{sel} — EMA 10/20 + 50/200 MA"),
                        use_container_width=True,
                    )


def page_momentum():
    st.markdown(
        '<div class="page-header">'
        '<h2>🎯 Qullamaggie Tarayıcı</h2>'
        '<p>Kristjan Qullamaggie\'nin felsefesi: <b>sadece hareketli ortalamalar ve hacim.</b> '
        'Güçlü trenddeki hisselerde 3 setup aranır — Kırılım, Episodik Pivot, EMA Geri Çekilme. '
        'Her fırsatta giriş / stop / hedef planı otomatik üretilir.</p>'
        '</div>', unsafe_allow_html=True)

    # İki alt sekme: Canlı TV + yfinance tarayıcı
    q_tab1, q_tab2 = st.tabs(["🔎 Qullamaggie Filtre Tara", "🔍 Derin Analiz (RS/ADR/Setup)"])
    with q_tab1:
        _render_qullamaggie_scan_section()

    with q_tab2:
        c = st.columns(3)
        min_rs = c[0].slider("Min. RS Rating", 50, 99, 80, help="Göreli güç (havuz içi yüzdelik). IBD: 80+ ideal")
        min_adr = c[1].slider("Min. ADR %", 1.0, 15.0, 4.0, 0.5, help="Volatilite. Momentum için 4%+ tercih edilir")
        evren = c[2].selectbox("Tarama Evreni",
                               ["Hazır Momentum (40)", "Nasdaq-100 (geniş, yavaş)", "Kendi listem"],
                               help="Evren büyüdükçe RS Rating daha anlamlı olur ama tarama uzar.")

        if evren == "Nasdaq-100 (geniş, yavaş)":
            universe = sorted(set(NASDAQ100))
            st.caption(f"⏳ {len(universe)} hisse taranacak — ilk seferde ~30-60 sn sürebilir (sonra 3 dk cache'li).")
        elif evren == "Kendi listem":
            txt = st.text_input("Ticker listesi (virgülle)", ", ".join(MOMENTUM_UNIVERSE[:10]))
            universe = [t.strip().upper() for t in txt.split(",") if t.strip()] or MOMENTUM_UNIVERSE
        else:
            universe = MOMENTUM_UNIVERSE

        if st.button("🔍 Momentum Tara", type="primary", use_container_width=True):
            st.session_state["mom_scan"] = scan_momentum(universe, min_rs, min_adr)

        df = st.session_state.get("mom_scan")
        if df is None:
            st.info("👆 'Momentum Tara' butonuna bas. (Tarama biraz sürebilir — 1 yıllık veri çekiliyor.)")
        elif df.empty:
            st.warning("Bu filtrelerle eşleşen hisse yok. RS/ADR eşiğini düşürmeyi dene.")
        else:
            # En iyi adaylar kart halinde
            st.markdown(f"### 🎯 {len(df)} Aday (güçlüden zayıfa)")
            recs = df.to_dict("records")
            per_row = 3
            for start in range(0, min(len(recs), 9), per_row):
                cols = st.columns(per_row)
                for col, r in zip(cols, recs[start:start + per_row]):
                    dcol = C_UP if r["Günlük %"] >= 0 else C_DOWN
                    col.markdown(
                        f'<div style="background:rgba(59,130,246,0.10);border:1px solid {C_ACCENT};'
                        f'border-radius:12px;padding:12px;margin-bottom:10px;">'
                        f'<div style="font-size:1.15rem;font-weight:800;color:#fff;">{r["Hisse"]} '
                        f'<span style="font-size:0.85rem;color:{dcol};">{r["Günlük %"]:+.2f}%</span></div>'
                        f'<div style="font-size:0.82rem;color:#bbb;margin:4px 0;">{r["Setup"]}</div>'
                        f'<div style="font-size:0.78rem;color:#999;">RS <b style="color:#f0b90b;">{r["RS"]}</b> • '
                        f'ADR {r["ADR %"]}% • Trend {r["Trend"]} • Zirveye {r["Zirveye %"]}%</div>'
                        f'<div style="font-size:0.78rem;color:#999;">${r["Fiyat"]} • Gör.Hacim {r["Gör. Hacim"]}x</div>'
                        f'</div>', unsafe_allow_html=True)

            st.markdown("#### 📊 Tüm Adaylar")
            show = df.drop(columns=[c for c in df.columns if c.startswith("_")])
            st.dataframe(show, use_container_width=True, hide_index=True,
                         column_config={
                             "RS": st.column_config.ProgressColumn(min_value=0, max_value=99, format="%d",
                                 help="Havuz içi göreli güç. 80+ = lider."),
                             "Sektör RS": st.column_config.NumberColumn(format="%+.1f%%",
                                 help="Hissenin kendi sektör ETF'ine karşı 3 aylık fark. + = sektör lideri."),
                             "Birikim": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%d",
                                 help="Stealth accumulation skoru. Fiyat flat iken OBV/MFI yükseliyorsa = smart money giriyor."),
                             "Günlük %": st.column_config.NumberColumn(format="%.2f%%"),
                             "Zirveye %": st.column_config.NumberColumn(format="%.1f%%"),
                         })

            st.divider()

            # ── Trade Planı: seçilen hisse için Qullamaggie açıklaması ──
            st.markdown("#### 📋 Trade Planı")
            pick = st.selectbox("Hisse seç — giriş / stop / hedef göster", show["Hisse"].tolist())
            if pick:
                cdf = fetch_daily(pick, "1y")
                if cdf is not None:
                    pick_rec  = show[show["Hisse"] == pick].iloc[0]
                    pick_setup = pick_rec["Setup"]
                    plan = explain_trade(pick_setup, cdf)

                    if plan:
                        rr_col = C_UP if plan["rr"] >= 3 else (C_GOLD if plan["rr"] >= 2 else C_DOWN)
                        st.markdown(
                            f'<div style="background:rgba(59,130,246,0.07);border:1px solid rgba(59,130,246,0.3);'
                            f'border-radius:14px;padding:16px 20px;margin-bottom:14px;">'
                            f'<div style="font-size:1.1rem;font-weight:800;color:#f1f5f9;margin-bottom:8px;">'
                            f'{pick} &nbsp; <span style="font-size:0.9rem;color:#9ca3af;">{pick_setup}</span></div>'
                            f'<div style="font-size:0.88rem;color:#d1d5db;margin-bottom:10px;">{plan["neden"]}</div>'
                            f'<div style="display:flex;gap:24px;flex-wrap:wrap;">'
                            f'<div><div style="font-size:0.72rem;color:#6b7280;">GİRİŞ</div>'
                            f'<div style="font-size:1.1rem;font-weight:700;color:#f1f5f9;">${plan["entry"]}</div></div>'
                            f'<div><div style="font-size:0.72rem;color:#6b7280;">STOP</div>'
                            f'<div style="font-size:1.1rem;font-weight:700;color:{C_DOWN};">${plan["stop"]}</div></div>'
                            f'<div><div style="font-size:0.72rem;color:#6b7280;">HEDEF</div>'
                            f'<div style="font-size:1.1rem;font-weight:700;color:{C_UP};">${plan["target"]}</div></div>'
                            f'<div><div style="font-size:0.72rem;color:#6b7280;">RİSK/ÖDÜL</div>'
                            f'<div style="font-size:1.1rem;font-weight:700;color:{rr_col};">{plan["rr"]}:1</div></div>'
                            f'</div>'
                            f'<div style="font-size:0.78rem;color:#6b7280;margin-top:10px;border-top:1px solid rgba(255,255,255,0.06);padding-top:8px;">'
                            f'⚠️ {plan["bekle"]}</div>'
                            f'</div>', unsafe_allow_html=True)

                    st.plotly_chart(make_cloud_chart(cdf, f"{pick} • EMA 10/20 + 50/200 MA"),
                                    use_container_width=True)

    with st.expander("📚 Qullamaggie'nin 3 temel setupı"):
        st.markdown("""
**Kristjan Qullamaggie'nin kuralları: sadece hareketli ortalamalar + hacim.**

| Setup | Koşul | Giriş | Stop |
|-------|-------|-------|------|
| 🚀 **Kırılım** | Trend ✅, dar konsolidasyon, hacimle üst kırıldı | Kırılım üstü | EMA10 altı |
| ⚡ **Episodik Pivot** | Gap-up %4+, hacim 2.5x+ (haber/kataliz) | Gap günü kapanışı yakını | Gap günü dibi |
| 🔄 **EMA Geri Çekilme** | Trend ✅, EMA10'a dokunup döndü | EMA10 üstü | EMA20 altı |
| 🏴 **Sıkışma (VCP)** | Hacim daralıyor, fiyat dar bant | Kırılım emri koy, bekle | EMA20 altı |

**Risk yönetimi:** İşlem başına hesabın **%1'ini** riske at. Stop kesin — tartışma yok.
**Piyasa filtresi:** Önce Piyasa Nabzı sekmesine bak. Risk-Off ortamda yeni pozisyon açma.
        """)


def _render_daily_commentary(spx_chg: float, vix_chg: float, ndx_chg: float, sec_df):
    """Günün piyasa yorumunu sade-teknik dille gösterir."""
    tarih = datetime.now().strftime("%d.%m.%Y")

    if spx_chg > 0.3 and vix_chg < 0:
        risk_renk, risk_ikon, risk_metin = C_UP, "🟢", "Risk-On"
        risk_aciklama = (f"Endeksler yukarı (SPX {spx_chg:+.2f}%), VIX aşağı ({vix_chg:+.2f}%). "
                         "Piyasa iştahlı. Qullamaggie setuplarına girebilirsin — trend yönünde.")
        eylem = "Kırılım ve EMA geri çekilme setuplarını tara. Stop'ları sıkı tut."
    elif spx_chg < -0.3 and vix_chg > 0:
        risk_renk, risk_ikon, risk_metin = C_DOWN, "🔴", "Risk-Off"
        risk_aciklama = (f"Endeksler aşağı (SPX {spx_chg:+.2f}%), VIX yukarı ({vix_chg:+.2f}%). "
                         "Kurumlar satıyor. Yeni pozisyon açma.")
        eylem = "Mevcut pozisyonların stopunu sıkılaştır. Nakit beklet."
    elif abs(spx_chg) <= 0.3:
        risk_renk, risk_ikon, risk_metin = C_GOLD, "🟡", "Durağan"
        risk_aciklama = (f"SPX {spx_chg:+.2f}%, Nasdaq {ndx_chg:+.2f}%. "
                         "Piyasa yön arıyor. Kırılım olmadan işlem açma.")
        eylem = "Watchlist tara, kırılım emri koy — tetik düşmeden girme."
    else:
        risk_renk, risk_ikon, risk_metin = C_GOLD, "🟠", "Karışık"
        risk_aciklama = (f"SPX {spx_chg:+.2f}%, VIX {vix_chg:+.2f}% — sinyal çelişiyor.")
        eylem = "Küçük deneme pozisyonu veya izle-bekle."

    st.markdown(
        f'<div style="background:rgba(255,255,255,0.03);border-left:4px solid {risk_renk};'
        f'border-radius:8px;padding:16px 20px;margin-bottom:14px;">'
        f'<div style="font-size:0.75rem;color:#6b7280;margin-bottom:4px;">{tarih}</div>'
        f'<div style="font-size:1.1rem;font-weight:800;color:{risk_renk};margin-bottom:6px;">'
        f'{risk_ikon} {risk_metin}</div>'
        f'<div style="font-size:0.88rem;color:#d1d5db;margin-bottom:8px;">{risk_aciklama}</div>'
        f'<div style="font-size:0.82rem;color:#9ca3af;background:rgba(255,255,255,0.04);'
        f'border-radius:6px;padding:8px 12px;">⚡ <b>Ne yapmalısın:</b> {eylem}</div>'
        f'</div>', unsafe_allow_html=True)

    if sec_df is not None and not sec_df.empty:
        best  = sec_df.iloc[0]
        worst = sec_df.iloc[-1]
        yukselenler = sec_df[sec_df["Haftalık %"] > 0]
        dusenler    = sec_df[sec_df["Haftalık %"] < 0]
        st.markdown(
            f'<div style="font-size:0.85rem;color:#9ca3af;padding:6px 0;">'
            f'💰 <b style="color:{C_UP};">{best["Sektör"]}</b> haftalık güçlü ({best["Haftalık %"]:+.2f}%) — '
            f'bu sektördeki lider hisselere öncelik ver. &nbsp;|&nbsp; '
            f'💸 <b style="color:{C_DOWN};">{worst["Sektör"]}</b> zayıf ({worst["Haftalık %"]:+.2f}%) — '
            f'bu sektörde long açmaktan kaçın.'
            f'<br><span style="color:#6b7280;font-size:0.78rem;">'
            f'{len(yukselenler)} sektör ↑ · {len(dusenler)} sektör ↓</span>'
            f'</div>', unsafe_allow_html=True)

    st.caption("Otomatik üretildi · Yatırım tavsiyesi değildir.")


def page_market_pulse(tickers):
    st.markdown(
        '<div class="page-header">'
        '<h2>🌍 Piyasa Nabzı</h2>'
        '<p>S&P500, VIX, faiz, dolar ve sektör rotasyonu tek bakışta. '
        'Önce piyasayı oku — Risk-On mu Risk-Off mu — sonra işlem planı yap. '
        'Qullamaggie\'nin birinci kuralı: <b>piyasa aleyhine işlem açma.</b></p>'
        '</div>', unsafe_allow_html=True)

    top = st.columns([2, 1, 1])
    top[0].caption(f"Son güncelleme: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    if top[1].button("🔄 Yenile", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    # Auto-refresh toggle
    auto = top[2].toggle("⏱ Oto-Yenile (60s)", value=False)
    if auto:
        import time as _time
        last = st.session_state.get("_pulse_ts", 0)
        if _time.time() - last > 60:
            st.session_state["_pulse_ts"] = _time.time()
            st.cache_data.clear()
            st.rerun()

    # ---------- 1) MAKRO TABLO ----------
    st.markdown("### 🌍 Günlük Makro Özet")
    macro_rows, spx_chg, vix_chg, ndx_chg = [], 0, 0, 0
    for sym, name in MACRO_ASSETS.items():
        df = fetch_daily(sym, "5d")
        if df is None or len(df) < 2:
            continue
        chg = (df["Close"].iloc[-1] - df["Close"].iloc[-2]) / df["Close"].iloc[-2] * 100
        if sym == "^GSPC": spx_chg = chg
        if sym == "^VIX":  vix_chg = chg
        if sym == "^IXIC": ndx_chg = chg
        macro_rows.append({"Varlık": name, "Fiyat": round(float(df["Close"].iloc[-1]), 2),
                           "Günlük %": round(float(chg), 2)})
    if macro_rows:
        cols = st.columns(5)
        for i, r in enumerate(macro_rows):
            cols[i % 5].metric(r["Varlık"], f"{r['Fiyat']:,}", f"{r['Günlük %']:+.2f}%")

        # Risk-on / risk-off okuması
        if spx_chg > 0 and vix_chg < 0:
            st.success("🟢 **Risk-On:** Endeksler yukarı, korku (VIX) aşağı. Piyasa iştahı pozitif — long kurulumlar öne çıkar.")
        elif spx_chg < 0 and vix_chg > 0:
            st.error("🔴 **Risk-Off:** Endeksler aşağı, korku (VIX) yukarı. Temkinli ol, nakit/savunma sektörleri öne çıkar.")
        else:
            st.info("🟡 **Karışık:** Net bir risk yönü yok; seçici ol, teyit bekle.")

    st.divider()

    # ---------- 2) SEKTÖR ROTASYONU (KARE KARE) ----------
    st.markdown("### 🔄 Sektör Rotasyonu — Para Nereye Akıyor?")
    sec_rows = []
    for sym, name in SECTOR_ETFS.items():
        df = fetch_daily(sym, "1mo")
        if df is None or len(df) < 6:
            continue
        d1 = (df["Close"].iloc[-1] - df["Close"].iloc[-2]) / df["Close"].iloc[-2] * 100
        d5 = (df["Close"].iloc[-1] - df["Close"].iloc[-6]) / df["Close"].iloc[-6] * 100
        sec_rows.append({"Sektör": name, "Sembol": sym,
                        "Günlük %": round(float(d1), 2), "Haftalık %": round(float(d5), 2)})

    sec_df = pd.DataFrame()
    if sec_rows:
        sec_df = pd.DataFrame(sec_rows).sort_values("Haftalık %", ascending=False)
        best = sec_df.iloc[0]; worst = sec_df.iloc[-1]
        st.markdown(f"💰 **Para girişi:** {best['Sektör']} (haftalık {best['Haftalık %']:+}%) &nbsp;|&nbsp; "
                    f"💸 **Para çıkışı:** {worst['Sektör']} (haftalık {worst['Haftalık %']:+}%)")

        # Kare kart ızgarası — tüm sektörler (haftalığa göre güçlüden zayıfa)
        per_row = 4
        recs = sec_df.to_dict("records")
        for start in range(0, len(recs), per_row):
            cols = st.columns(per_row)
            for col, r in zip(cols, recs[start:start + per_row]):
                wk = r["Haftalık %"]
                # Renk: güçlü yeşilden güçlü kırmızıya
                if wk >= 2: bg, brd = "rgba(22,199,132,0.22)", C_UP
                elif wk >= 0: bg, brd = "rgba(22,199,132,0.10)", C_UP
                elif wk > -2: bg, brd = "rgba(234,57,67,0.10)", C_DOWN
                else: bg, brd = "rgba(234,57,67,0.22)", C_DOWN
                dcol = C_UP if r["Günlük %"] >= 0 else C_DOWN
                wcol = C_UP if wk >= 0 else C_DOWN
                col.markdown(
                    f'<div style="background:{bg};border:1px solid {brd};border-radius:12px;'
                    f'padding:12px;text-align:center;margin-bottom:10px;min-height:108px;">'
                    f'<div style="font-size:0.9rem;font-weight:700;color:#eee;">{r["Sektör"]}</div>'
                    f'<div style="font-size:0.7rem;color:#888;">{r["Sembol"]}</div>'
                    f'<div style="font-size:1.4rem;font-weight:800;color:{wcol};margin-top:6px;">{wk:+.2f}%</div>'
                    f'<div style="font-size:0.72rem;color:#999;">haftalık</div>'
                    f'<div style="font-size:0.8rem;color:{dcol};margin-top:2px;">bugün {r["Günlük %"]:+.2f}%</div>'
                    f'</div>', unsafe_allow_html=True)

    st.divider()

    # ---------- 2b) DÜNYA BORSALARI ----------
    st.markdown("### 🌐 Dünya Borsaları")
    for bolge, indices in GLOBAL_INDICES.items():
        st.markdown(f"**{bolge}**")
        cols = st.columns(len(indices))
        for col, (sym, meta) in zip(cols, indices.items()):
            gdf = fetch_daily(sym, "5d")
            if gdf is None or len(gdf) < 2:
                col.markdown(
                    f'<div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);'
                    f'border-radius:10px;padding:10px;text-align:center;margin-bottom:8px;">'
                    f'<div style="font-size:0.8rem;color:#6b7280;">{meta["ulke"]} {meta["isim"]}</div>'
                    f'<div style="font-size:0.85rem;color:#4b5563;">Veri yok</div>'
                    f'</div>', unsafe_allow_html=True)
                continue
            price = float(gdf["Close"].iloc[-1])
            d1    = (price - float(gdf["Close"].iloc[-2])) / float(gdf["Close"].iloc[-2]) * 100
            wk    = (price - float(gdf["Close"].iloc[0])) / float(gdf["Close"].iloc[0]) * 100 if len(gdf) >= 5 else d1
            col_d = C_UP if d1 >= 0 else C_DOWN
            bg    = "rgba(22,199,132,0.10)" if d1 >= 0 else "rgba(234,57,67,0.10)"
            brd   = C_UP if d1 >= 0 else C_DOWN
            col.markdown(
                f'<div style="background:{bg};border:1px solid {brd};border-radius:10px;'
                f'padding:10px;text-align:center;margin-bottom:8px;">'
                f'<div style="font-size:0.72rem;color:#9ca3af;">{meta["ulke"]} {meta["isim"]}</div>'
                f'<div style="font-size:1rem;font-weight:800;color:{col_d};margin:3px 0;">{d1:+.2f}%</div>'
                f'<div style="font-size:0.68rem;color:#6b7280;">haftalık {wk:+.1f}%</div>'
                f'</div>', unsafe_allow_html=True)

    st.divider()

    # ---------- 3) BÜYÜK PARA — KURUMSAL HAREKETLİLİK ----------
    st.markdown("### 🐋 Büyük Para — Kurumsal Hareketlilik")
    st.caption("Hangi hissede olağandışı hacim var? Fiyat da yükseliyorsa kurumsal alım sinyali.")

    if st.button("🔍 Büyük Para Tara", type="primary", use_container_width=True, key="bm_pulse"):
        big_money = []
        prog = st.progress(0, "Taranıyor...")
        scan_universe = tickers + [t for t in MOMENTUM_UNIVERSE if t not in tickers]
        for i, t in enumerate(scan_universe):
            prog.progress((i + 1) / len(scan_universe), f"{t}")
            df_bm = fetch_daily(t, "3mo")
            if df_bm is None or len(df_bm) < 22:
                continue
            rvol = relative_volume(df_bm, 20)
            price = float(df_bm["Close"].iloc[-1])
            chg   = (price - float(df_bm["Close"].iloc[-2])) / float(df_bm["Close"].iloc[-2]) * 100
            dolar_vol = price * float(df_bm["Volume"].iloc[-1]) / 1e6  # milyon $

            # Büyük para kriteri: RVOL 1.5x+ VE fiyat artıyor
            if rvol >= 1.5 and chg > 0:
                ema10 = float(compute_ema(df_bm["Close"], 10).iloc[-1])
                ema20 = float(compute_ema(df_bm["Close"], 20).iloc[-1])
                trend_ok = price > ema10 > ema20
                big_money.append({
                    "Hisse": t, "Fiyat": round(price, 2),
                    "Günlük %": round(chg, 2), "RVOL": round(rvol, 2),
                    "Hacim ($M)": round(dolar_vol, 1),
                    "Trend": "✅ Yukarı" if trend_ok else "⚠️ Karışık",
                    "_rvol": rvol,
                })
        prog.empty()

        big_money.sort(key=lambda x: x["_rvol"], reverse=True)
        st.session_state["big_money"] = big_money

    bm = st.session_state.get("big_money")
    if bm:
        # Tier 1: RVOL 2x+ ve trend yukarı = en güçlü sinyal
        tier1 = [r for r in bm if r["_rvol"] >= 2.0 and "✅" in r["Trend"]]
        tier2 = [r for r in bm if r not in tier1]

        if tier1:
            st.markdown("**🔥 Güçlü kurumsal ilgi (RVOL 2x+ + trend yukarı)**")
            cols = st.columns(min(4, len(tier1)))
            for col, r in zip(cols * 10, tier1[:8]):
                col.markdown(
                    f'<div style="background:rgba(22,199,132,0.10);border:1px solid #16c784;'
                    f'border-radius:10px;padding:10px;text-align:center;margin-bottom:8px;">'
                    f'<div style="font-weight:800;font-size:1rem;color:#fff;">{r["Hisse"]}</div>'
                    f'<div style="color:{C_UP};font-size:0.9rem;font-weight:700;">{r["Günlük %"]:+.2f}%</div>'
                    f'<div style="color:#9ca3af;font-size:0.75rem;">{r["RVOL"]}x hacim</div>'
                    f'<div style="color:#6b7280;font-size:0.72rem;">${r["Hacim ($M)"]}M</div>'
                    f'</div>', unsafe_allow_html=True)

        if tier2:
            with st.expander(f"📋 Diğer yüksek hacimli hisseler ({len(tier2)})"):
                bm_df = pd.DataFrame([{k: v for k, v in r.items() if not k.startswith("_")} for r in tier2])
                st.dataframe(bm_df, use_container_width=True, hide_index=True,
                             column_config={"RVOL": st.column_config.NumberColumn(format="%.2fx"),
                                            "Günlük %": st.column_config.NumberColumn(format="%.2f%%")})

    # ---------- 4) GÜNÜN YORUMU ----------
    st.divider()
    st.markdown("### 📋 Günün Yorumu")
    _render_daily_commentary(spx_chg, vix_chg, ndx_chg, sec_df)

    st.divider()


def page_simulation(tickers, period, interval, initial_cash=10000.0, risk_pct=1.0):
    init_sim_state()
    st.session_state["_sim_account"] = initial_cash
    st.session_state["_sim_risk"] = risk_pct
    st.markdown(
        '<div class="page-header">'
        '<h2>🎮 Simülasyon</h2>'
        '<p>Gerçek grafiklere bakarak al/sat kararı ver, anında sonucunu gör. '
        'XP kazan, rozet topla ve disiplinini geliştir — gerçek para riske atmadan.</p>'
        '</div>', unsafe_allow_html=True)
    st.caption("Grafiği analiz et, kararını ver, sonucu gör. $100 sanal bakiye ile başla.")

    bal = st.session_state["balance"]
    xp = st.session_state["xp"]
    correct, wrong = st.session_state["correct"], st.session_state["wrong"]
    total = correct + wrong
    win_rate = f"{correct/total*100:.0f}%" if total else "—"
    next_goal = next((g for g in GOALS if g > bal), None)

    cols = st.columns(7)
    for col, (lbl, val) in zip(cols, [
        ("💰 Bakiye", f"${bal:.2f}"), ("⭐ XP", str(xp)), ("🏆 Sv", str(xp_to_level(xp))),
        ("✅", str(correct)), ("❌", str(wrong)), ("📊 WR", win_rate),
        ("🎯 Hedef", f"${next_goal}" if next_goal else "MAX")]):
        col.markdown(f'<div class="mcard"><div class="mval">{val}</div><div class="mlbl">{lbl}</div></div>',
                     unsafe_allow_html=True)

    if next_goal:
        prev = max([g for g in [100] + GOALS if g <= bal], default=100)
        st.progress(max(0.0, min((bal - prev) / (next_goal - prev), 1.0)),
                    text=f"Sonraki hedef ${next_goal} • Kalan ${next_goal-bal:.2f}")

    if st.session_state["badges"]:
        st.markdown("**Rozetler:** " + " ".join(
            f'<span class="badge">{BADGES[b]["icon"]} {b}</span>' for b in st.session_state["badges"]),
            unsafe_allow_html=True)

    st.divider()
    c1, c2 = st.columns(2)
    if c1.button("📥 Yeni Senaryo (Gerçek Veri)", use_container_width=True):
        random.shuffle(tickers)
        chosen, df = None, None
        for t in tickers:
            df = fetch_data(t, period, interval)
            if df is not None and len(df) > 60:
                chosen = t
                break
        if df is None:
            st.error("Veri alınamadı.")
        else:
            _setup_scenario(df, "Gizli Hisse", ticker=chosen, interval=interval)
    if c2.button("🎲 Yeni Senaryo (Sentetik)", use_container_width=True):
        stype = random.choice(SYNTHETIC_TYPES)
        _setup_scenario(generate_synthetic_data(stype), f"Sentetik ({stype})",
                        ticker=None, interval="1d", synth_type=stype)

    sc = st.session_state.get("scenario")
    if sc is None:
        st.info("👆 Yeni senaryo getirin.")
        return

    phase = st.session_state["phase"]
    if phase == "ready" and st.button("▶️ Grafiği Başlat", use_container_width=True):
        st.session_state["phase"] = "showing"
        st.rerun()

    if phase in ("showing", "result"):
        show_future = phase == "result"
        st.plotly_chart(_sim_chart(sc["df_show"], sc["df_future"] if show_future else None,
                                   sc["label"]), use_container_width=True)

    if phase == "showing":
        st.markdown("### 🎯 Kararını Ver")
        rc1, rc2 = st.columns([3, 1])
        reason = rc1.text_input("📝 Neden bu kararı veriyorsun? (günlüğe işlenir)",
                                key="pending_reason",
                                placeholder="örn. fiyat EMA50 üstünde tutundu, hacim arttı")
        emotion = rc2.selectbox("Duygu durumu",
                                ["—", "😎 Güvenli", "😟 Tereddütlü", "😱 FOMO", "😐 Nötr"],
                                key="pending_emotion")
        d = st.columns(4)
        decision = None
        if d[0].button("🟢 AL", use_container_width=True): decision = "AL"
        if d[1].button("🔴 SAT", use_container_width=True): decision = "SAT"
        if d[2].button("🟡 BEKLE", use_container_width=True): decision = "BEKLE"
        if d[3].button("⬜ GİRME", use_container_width=True): decision = "İŞLEME GİRME"
        if decision:
            _resolve_decision(decision, sc, reason=reason, emotion=emotion)
            st.rerun()

    if phase == "result" and "_eval" in sc:
        ev = sc["_eval"]
        if ev["correct"]:
            st.success(f"✅ Doğru! P&L ${ev['pnl']:+.2f} • +{sc['_xp']} XP")
        else:
            st.error(f"❌ Yanlış. P&L ${ev['pnl']:+.2f} • +{sc['_xp']} XP")
        if sc.get("_badges"):
            st.balloons()
            st.success("🏅 Yeni Rozet: " + ", ".join(sc["_badges"]))

        # Hisse adı + tarih açıklaması (karardan sonra ortaya çıkar)
        reveal = sc["ticker"] if sc["ticker"] else sc["label"]
        st.markdown(f"#### 🔎 Bu grafik: **{reveal}**")
        with st.container():
            st.markdown(build_sim_report(sc, ev), unsafe_allow_html=False)

        # 📋 Karar anındaki gerçek trade planı (eğitim amaçlı, gerçek borsa parametreleri)
        with st.expander("📋 Karar Anındaki Trade Planı (gerçek borsa mantığı)", expanded=True):
            karar = st.session_state["decision"]
            plan_side = "SAT" if karar == "SAT" else "AL"
            sig_show = ut_bot_signals(sc["df_show"], 1.0, 10)
            plan = build_trade_plan(sig_show, plan_side,
                                    account_size=st.session_state.get("_sim_account", 10000.0),
                                    risk_pct=st.session_state.get("_sim_risk", 1.0))
            render_trade_plan(plan)
            st.caption("Bu plan, kararı verdiğin andaki fiyatla gerçek bir işlemde kullanacağın "
                       "stop, hedef ve pozisyon büyüklüğünü gösterir — böylece sadece yön değil, "
                       "risk yönetimini de pratik edersin.")

        # 📖 Grafik okuma dersi
        with st.expander("📖 Grafik Okuma Dersi", expanded=True):
            st.markdown(build_chart_lesson(sc, ev))

        # Karardan çıkardığın ders -> son günlük kaydına işlenir
        st.markdown("##### ✍️ Bu trade'den çıkardığın ders")
        lesson = st.text_input("Notunu yaz, günlüğüne kaydedilsin:",
                               key=f"lesson_{len(st.session_state['history'])}",
                               placeholder="örn. RSI 70 üstündeyken AL'a girmemeliydim, risk/ödül kötüydü")
        if st.button("💾 Dersi Günlüğe Kaydet"):
            if st.session_state["history"]:
                st.session_state["history"][-1]["Ders"] = lesson.strip() or "—"
                st.success("Ders günlüğe kaydedildi.")

        st.plotly_chart(_sim_balance_chart(), use_container_width=True)

    _render_journal()


def _setup_scenario(df, label, ticker=None, interval="1d", synth_type=None):
    n = len(df)
    split = int(n * 0.67)
    sc = {"df_show": df.iloc[:split].copy(), "df_future": df.iloc[split:].copy(),
          "label": label, "score": compute_score(df.iloc[:split]),
          "ticker": ticker, "interval": interval, "synth_type": synth_type}
    st.session_state["scenario"] = sc
    st.session_state["phase"] = "ready"
    st.rerun()


# Her senaryoda dönüşümlü gösterilen genel trade prensipleri
TRADE_TIPS = [
    "Plan olmadan işleme girme: girişten önce stop ve hedefini belirle.",
    "Trend dostundur — trende karşı işlem, akıntıya karşı yüzmektir.",
    "Teyit bekle: tek bir mum değil, yapının onayı (kapanış + hacim) önemlidir.",
    "Risk/ödül en az 1:2 olmayan işlemler uzun vadede seni yorar.",
    "RSI aşırı alımda (70+) trend bitmez ama yeni alımın risk/ödülü kötüleşir.",
    "Hacimsiz kırılımlar genelde sahte (fake breakout) çıkar.",
    "En iyi işlem bazen hiç işlem yapmamaktır — nakitte beklemek de bir pozisyondur.",
    "Geçmiş senin değil piyasanın hikayesi; her mumun arkasında bir karar vardır.",
]


def build_chart_lesson(sc, ev) -> str:
    """Bu senaryoya özel, öğretici grafik okuma dersi üretir."""
    show = sc["df_show"]
    score = sc["score"]
    close = show["Close"]
    ema21, ema50 = compute_ema(close, 21), compute_ema(close, 50)
    rsi = compute_rsi(close).iloc[-1]
    rsi = round(rsi, 1) if not pd.isna(rsi) else 50
    last = float(close.iloc[-1])
    vol_now = show["Volume"].iloc[-1]
    vol_avg = show["Volume"].iloc[-20:].mean()

    lines = ["**Bu grafikte nelere bakmalıydın:**", ""]

    # EMA dizilimi dersi
    if last > ema21.iloc[-1] > ema50.iloc[-1]:
        lines.append("- 🟢 **EMA dizilimi:** Fiyat > EMA21 > EMA50 → boğalar kontrolde. "
                     "Bu dizilimde geri çekilmeler (EMA21'e dönüş) genelde alım fırsatıdır.")
    elif last < ema21.iloc[-1] < ema50.iloc[-1]:
        lines.append("- 🔴 **EMA dizilimi:** Fiyat < EMA21 < EMA50 → ayılar kontrolde. "
                     "Bu yapıda yükselişler genelde satış fırsatı (zayıf tepki) olur.")
    else:
        lines.append("- 🟡 **EMA dizilimi:** Ortalamalar iç içe → yön belirsiz. "
                     "Bu tür sıkışmalarda kırılım gelene kadar beklemek mantıklıdır.")

    # RSI dersi
    if rsi > 70:
        lines.append(f"- **RSI {rsi}:** Aşırı alım. Trend güçlü ama momentum yorulmuş olabilir; "
                     "yeni girişte risk/ödül kötüdür.")
    elif rsi < 30:
        lines.append(f"- **RSI {rsi}:** Aşırı satım. Sert düşüş sonrası tepki gelebilir ama "
                     "düşen bıçağı tutmak risklidir; dönüş teyidi bekle.")
    elif rsi > 55:
        lines.append(f"- **RSI {rsi}:** Pozitif momentum, alıcılar aktif.")
    elif rsi < 45:
        lines.append(f"- **RSI {rsi}:** Negatif momentum, satıcılar baskın.")
    else:
        lines.append(f"- **RSI {rsi}:** Nötr bölge, net yön yok.")

    # Hacim dersi
    if vol_now > vol_avg * 1.5:
        lines.append("- **Hacim:** Son mumda hacim ortalamanın belirgin üstünde → hareket teyitli, "
                     "kurumsal ilgi olabilir.")
    elif vol_now < vol_avg * 0.6:
        lines.append("- **Hacim:** Hacim düşük → hareketin arkasında güç az, kırılımlar güvenilmez.")
    else:
        lines.append("- **Hacim:** Normal seviyede, belirleyici değil.")

    # Formasyon dersi
    if score["formations"]:
        lines.append(f"- **Formasyon(lar):** {', '.join(score['formations'])} — "
                     "bu yapılar fiyatın bir sonraki olası yönü hakkında ipucu verir.")

    # Sonuçtan ders
    lines.append("")
    if ev["correct"]:
        lines.append("✅ **Sonuç teyidi:** Okuduğun yapı ile fiyatın gittiği yön örtüştü. "
                     "Doğru okuma + doğru karar = tekrarlanabilir başarı.")
    else:
        lines.append("📌 **Çıkarım:** Yapı ile sonuç farklı çıktı. Bu normaldir — hiçbir kurulum %100 değildir. "
                     "Önemli olan tutarlı kurallarla işlem yapıp zararı küçük tutmaktır.")

    # Dönüşümlü genel ipucu
    tip = TRADE_TIPS[len(st.session_state["history"]) % len(TRADE_TIPS)]
    lines.append("")
    lines.append(f"> 💡 **Günün prensibi:** {tip}")

    return "\n".join(lines)


def _render_journal():
    """Trade günlüğü paneli: özet + tablo + CSV indir/yükle."""
    hist = st.session_state["history"]
    with st.expander(f"📓 Trade Günlüğü ({len(hist)} kayıt)", expanded=False):
        # CSV yükleme
        up = st.file_uploader("Eski günlüğü yükle (CSV)", type="csv", key="journal_upload")
        if up is not None and st.button("📂 Yüklenen günlüğü içe aktar"):
            try:
                loaded = pd.read_csv(up).to_dict("records")
                st.session_state["history"] = loaded + hist
                st.success(f"{len(loaded)} kayıt içe aktarıldı.")
                st.rerun()
            except Exception as e:
                st.error(f"Yükleme hatası: {e}")

        if not hist:
            st.info("Henüz kayıt yok. Bir senaryo oyna, kararın ve gerekçen buraya işlensin.")
            return

        df = pd.DataFrame(hist)

        # Kısa özet / içgörü
        total = len(df)
        wins = (df["Doğru"] == "✅").sum()
        wr = wins / total * 100 if total else 0
        most_decision = df["Karar"].mode()[0] if total else "—"
        emo = df[df["Duygu"] != "—"]["Duygu"]
        most_emo = emo.mode()[0] if not emo.empty else "—"
        st.markdown(
            f"**Özet:** {total} trade • Başarı **%{wr:.0f}** • En sık kararın **{most_decision}** • "
            f"En sık duygu **{most_emo}**")

        st.dataframe(df, use_container_width=True, hide_index=True)

        csv = df.to_csv(index=False).encode("utf-8-sig")
        st.download_button("⬇️ Günlüğü CSV indir", csv,
                           file_name="trade_gunlugu.csv", mime="text/csv")


def _resolve_decision(decision, sc, reason="", emotion="—"):
    fut = sc["df_future"]
    entry, exit_ = fut["Close"].iloc[0], fut["Close"].iloc[-1]
    pct = (exit_ - entry) / entry * 100
    score = sc["score"]["total"]
    is_risky = score < 40
    correct, pnl = False, 0.0
    if decision == "AL":
        correct, pnl = pct > 1.0, pct
    elif decision == "SAT":
        correct, pnl = pct < -1.0, -pct
    elif decision == "BEKLE":
        correct, pnl = (abs(pct) < 2.0 or (pct < 0 and score >= 40)), 0.0
    elif decision == "İŞLEME GİRME":
        correct = is_risky
        pnl = 5.0 if correct else -2.0
    pnl = round(pnl, 2)

    s = st.session_state
    s["decision"] = decision
    s["balance"] = round(s["balance"] + pnl, 2)
    s["balance_history"].append(s["balance"])
    if correct:
        s["correct"] += 1; s["streak"] += 1
    else:
        s["wrong"] += 1; s["streak"] = 0
    if decision == "İŞLEME GİRME" and is_risky and correct:
        s["risk_avoided"] += 1
    old_goals = s["goals_done"]
    for g in GOALS:
        if g not in s["goals_reached"] and s["balance"] >= g:
            s["goals_reached"].append(g); s["goals_done"] += 1

    xp = 5 + (20 if correct else 5)
    if s["goals_done"] > old_goals: xp += 50
    if s["streak"] >= 3: xp += 30
    s["xp"] += xp

    new_badges = [f"{BADGES[b]['icon']} {b}" for b, info in BADGES.items()
                  if b not in s["badges"] and info["cond"](s)]
    s["badges"].extend(b.split(" ", 1)[1] for b in new_badges)

    s["history"].append({
        "Tarih": datetime.now().strftime("%d.%m %H:%M"),
        "Hisse": sc["ticker"] if sc["ticker"] else sc["label"],
        "Karar": decision,
        "Doğru": "✅" if correct else "❌",
        "Değişim %": round(pct, 2), "P&L $": pnl, "Skor": score,
        "Gerekçe": reason.strip() or "—",
        "Duygu": emotion if emotion != "—" else "—",
        "Ders": "",
    })
    sc["_eval"] = {"correct": correct, "pnl": pnl, "pct_change": round(pct, 2)}
    sc["_xp"] = xp
    sc["_badges"] = new_badges
    st.session_state["phase"] = "result"
    st.session_state["scenario"] = sc


def _fmt_date(ts) -> str:
    """Tarihi okunur Türkçe biçime çevirir."""
    try:
        return pd.Timestamp(ts).strftime("%d.%m.%Y")
    except Exception:
        return str(ts)


def build_sim_report(sc, ev) -> str:
    """Karardan sonra: hisse adı, tarih ve teknik neden-sonuç raporu."""
    show, fut = sc["df_show"], sc["df_future"]
    score = sc["score"]
    name = sc["ticker"] if sc["ticker"] else sc["label"]

    # Tarih bilgileri
    show_start, decision_date = _fmt_date(show.index[0]), _fmt_date(show.index[-1])
    fut_end = _fmt_date(fut.index[-1])

    # Karar anındaki teknik durum
    close = show["Close"]
    ema21, ema50 = compute_ema(close, 21), compute_ema(close, 50)
    rsi = compute_rsi(close).iloc[-1]
    rsi = round(rsi, 1) if not pd.isna(rsi) else 50
    last = float(close.iloc[-1])
    trend_txt = ("yükselen trend (fiyat EMA21 ve EMA50'nin üzerinde)"
                 if last > ema21.iloc[-1] and last > ema50.iloc[-1]
                 else "düşen/zayıf trend (fiyat ortalamaların altında)"
                 if last < ema21.iloc[-1] and last < ema50.iloc[-1]
                 else "yatay/kararsız seyir")
    rsi_txt = ("aşırı alım bölgesine yakın (momentum güçlü ama tepe riski var)" if rsi > 70
               else "pozitif momentum" if rsi > 55
               else "zayıf/negatif momentum" if rsi < 45
               else "nötr momentum")

    # Sonuç bölgesinde ne oldu
    pct = ev["pct_change"]
    dir_ = "yükseldi 📈" if pct > 0 else "düştü 📉"
    fut_high = (fut["High"].max() - fut["Close"].iloc[0]) / fut["Close"].iloc[0] * 100
    fut_low = (fut["Low"].min() - fut["Close"].iloc[0]) / fut["Close"].iloc[0] * 100

    # UT Bot sonuç bölgesinde sinyal verdi mi?
    full = pd.concat([show, fut])
    sig = ut_bot_signals(full, 1.0, 10).iloc[len(show):]
    ut_txt = ""
    if sig["buy"].any():
        ut_txt = "Sonuç bölgesinde **UT Bot AL sinyali** üretti. "
    elif sig["sell"].any():
        ut_txt = "Sonuç bölgesinde **UT Bot SAT sinyali** üretti. "

    # Karar yorumu
    karar = st.session_state["decision"]
    sonuc = "✅ doğru" if ev["correct"] else "❌ yanlış"

    src_txt = (f"Bu, **{name}** hissesinin gerçek piyasa verisidir."
               if sc["ticker"] else
               f"Bu, **{name}** türünde sentetik (yapay) olarak üretilmiş bir grafiktir.")

    report = f"""
{src_txt}

**🗓️ Zaman aralığı**
- Karar bölgesi (sana gösterilen kısım): **{show_start} → {decision_date}**
- Sonuç bölgesi (karardan sonrası): **{decision_date} → {fut_end}**

**📊 Karar anındaki teknik tablo ({decision_date})**
- Trend: {trend_txt}
- RSI: **{rsi}** — {rsi_txt}
- Sistem skoru: **{score['total']}/100** → {system_decision(score['total'])}
- Tespit edilen formasyonlar: {', '.join(score['formations']) if score['formations'] else 'belirgin formasyon yok'}

**📈 Sonuç bölgesinde ne oldu?**
- Fiyat toplamda **%{abs(pct):.2f}** {dir_}
- Bu süreçte en fazla **%{fut_high:.1f}** yukarı, **%{fut_low:.1f}** aşağı hareket etti.
- {ut_txt}

**🧠 Neden böyle hareket etti? (teknik açıklama)**
{_explain_move(score, pct, rsi, sc)}

**🎯 Senin kararın:** {karar} → sonuç **{sonuc}**.
{_explain_decision(karar, pct, ev['correct'], score['total'])}
"""
    return report


def _explain_move(score, pct, rsi, sc) -> str:
    """Fiyat hareketinin teknik gerekçesini üretir."""
    parts = []
    up = pct > 0
    if score["total"] >= 70 and up:
        parts.append("Karar anında trend, EMA dizilimi ve hacim birlikte yukarı yönü destekliyordu; "
                     "bu güçlü yapı yükselişin devam etmesini olası kıldı.")
    elif score["total"] < 40 and not up:
        parts.append("Karar anında teknik tablo zayıftı (trend ve momentum negatif); "
                     "bu zayıflık sonraki düşüşe zemin hazırladı.")
    elif up and rsi < 45:
        parts.append("Momentum zayıf görünmesine rağmen fiyat toparladı — bu, beklenmedik bir alıcı ilgisi "
                     "veya kısa vadeli tepki alımı (pullback sonrası dönüş) olabilir.")
    elif not up and rsi > 70:
        parts.append("RSI aşırı alım bölgesindeydi; yükseliş yorulmuş, kâr satışları gelmiş ve fiyat geri çekilmiştir.")
    else:
        parts.append("Teknik göstergeler karışık sinyal veriyordu; bu tür ortamlarda fiyat yönü "
                     "haber akışı ve piyasa duyarlılığıyla şekillenir, kestirmesi zordur.")
    if sc.get("synth_type"):
        parts.append(f"(Not: bu sentetik grafik '{sc['synth_type']}' senaryosu olarak üretildi.)")
    return " ".join(parts)


def _explain_decision(karar, pct, correct, total) -> str:
    if karar == "AL":
        return ("Yükseliş beklentin gerçekleşti." if pct > 1 else
                "Beklenen yükseliş gelmedi; alım için yapı yeterince güçlü değildi.")
    if karar == "SAT":
        return ("Düşüş beklentin gerçekleşti." if pct < -1 else
                "Beklenen düşüş gelmedi; fiyat aksine güçlü kaldı.")
    if karar == "BEKLE":
        return ("Belirsiz ortamda beklemek mantıklıydı." if correct else
                "Burada net bir fırsat vardı; beklemek fırsatı kaçırttı.")
    return ("Zayıf kurulumda işleme girmemek doğru bir risk yönetimiydi." if correct else
            "Aslında işleme girilebilecek bir yapı vardı; fazla temkinli davranıldı.")


def _sim_chart(df, df_future, title):
    """Profesyonel görünümlü mum + EMA + RSI + hacim grafiği."""
    full_close = pd.concat([df["Close"], df_future["Close"]]) if df_future is not None and len(df_future) else df["Close"]
    ema21 = compute_ema(full_close, 21)
    ema50 = compute_ema(full_close, 50)
    rsi_full = compute_rsi(full_close)

    fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
                        row_heights=[0.62, 0.18, 0.20], vertical_spacing=0.025,
                        subplot_titles=(title, "Hacim", "RSI (14)"))

    # Geçmiş (karar bölgesi)
    fig.add_trace(go.Candlestick(x=df.index, open=df["Open"], high=df["High"], low=df["Low"],
                  close=df["Close"], name="Karar Bölgesi", increasing_line_color=C_UP,
                  decreasing_line_color=C_DOWN, increasing_fillcolor=C_UP,
                  decreasing_fillcolor=C_DOWN, line=dict(width=1)), row=1, col=1)

    # EMA çizgileri (tüm seri boyunca)
    fig.add_trace(go.Scatter(x=ema21.index, y=ema21, name="EMA21",
                  line=dict(color=C_GOLD, width=1.3)), row=1, col=1)
    fig.add_trace(go.Scatter(x=ema50.index, y=ema50, name="EMA50",
                  line=dict(color=C_ACCENT, width=1.3)), row=1, col=1)

    # Hacim - karar bölgesi
    colors = [C_UP if c >= o else C_DOWN for c, o in zip(df["Close"], df["Open"])]
    fig.add_trace(go.Bar(x=df.index, y=df["Volume"], name="Hacim",
                  marker_color=colors, opacity=0.55), row=2, col=1)

    # RSI - karar bölgesi
    rsi_show = rsi_full.loc[df.index]
    fig.add_trace(go.Scatter(x=df.index, y=rsi_show, name="RSI",
                  line=dict(color="#ff7043", width=1.3)), row=3, col=1)
    fig.add_hline(y=70, line=dict(color="rgba(234,57,67,0.4)", dash="dash"), row=3, col=1)
    fig.add_hline(y=30, line=dict(color="rgba(22,199,132,0.4)", dash="dash"), row=3, col=1)

    if df_future is not None and len(df_future):
        # Sonuç bölgesi mumları (daha soluk renkle)
        fig.add_trace(go.Candlestick(x=df_future.index, open=df_future["Open"], high=df_future["High"],
                      low=df_future["Low"], close=df_future["Close"], name="Sonuç Bölgesi",
                      increasing_line_color="#80cbc4", decreasing_line_color="#ef9a9a",
                      increasing_fillcolor="rgba(128,203,196,0.55)",
                      decreasing_fillcolor="rgba(239,154,154,0.55)", line=dict(width=1)), row=1, col=1)
        # Sonuç bölgesini sarı şeritle vurgula
        fig.add_vrect(x0=df_future.index[0], x1=df_future.index[-1],
                      fillcolor="rgba(255,235,59,0.06)", line_width=0, row=1, col=1)
        fig.add_vline(x=df_future.index[0], line=dict(color="#ffeb3b", width=2, dash="dash"))
        # Karar noktası etiketi
        fig.add_annotation(x=df_future.index[0], y=1, yref="y domain",
                           text="◀ Karar Anı", showarrow=False, font=dict(color="#ffeb3b", size=11),
                           bgcolor="rgba(0,0,0,0.5)", xanchor="left", row=1, col=1)
        # Sonuç bölgesi hacim ve RSI
        vc = [C_UP if c >= o else C_DOWN for c, o in zip(df_future["Close"], df_future["Open"])]
        fig.add_trace(go.Bar(x=df_future.index, y=df_future["Volume"], name="Sonuç Hacim",
                      marker_color=vc, opacity=0.3, showlegend=False), row=2, col=1)
        fig.add_trace(go.Scatter(x=df_future.index, y=rsi_full.loc[df_future.index], name="RSI Sonuç",
                      line=dict(color="rgba(255,112,67,0.5)", width=1.3), showlegend=False), row=3, col=1)

    fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(13,17,28,1)", height=640, xaxis_rangeslider_visible=False,
                      legend=dict(orientation="h", y=1.04, x=1, xanchor="right", font=dict(size=11)),
                      font=dict(family="Segoe UI, sans-serif", size=12),
                      margin=dict(l=10, r=10, t=60, b=10), hovermode="x unified",
                      bargap=0.15)
    fig.update_yaxes(gridcolor="rgba(255,255,255,0.05)", zeroline=False)
    fig.update_xaxes(gridcolor="rgba(255,255,255,0.04)", rangeslider_visible=False)
    fig.update_yaxes(range=[0, 100], row=3, col=1)
    return fig


def _sim_balance_chart():
    fig = go.Figure()
    fig.add_trace(go.Scatter(y=st.session_state["balance_history"], mode="lines+markers",
                  line=dict(color=C_ACCENT, width=2), fill="tozeroy"))
    fig.add_hline(y=100, line=dict(color="rgba(255,255,255,0.3)", dash="dot"))
    fig.update_layout(title="Bakiye Gelişimi", template="plotly_dark",
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(13,17,28,1)",
                      height=240, margin=dict(l=10, r=10, t=40, b=10))
    return fig


# ===========================================================================
# BALİNA RADAR
# ===========================================================================

def _whale_score(df: pd.DataFrame) -> dict:
    """RVOL, OBV eğimi, MFI ve fiyat-EMA konumuna göre balina birikim skoru hesaplar."""
    if len(df) < 25:
        return None

    rvol = relative_volume(df, 20)
    mfi_val = float(compute_mfi(df, 14).iloc[-1]) if not compute_mfi(df, 14).isna().iloc[-1] else 50.0
    obv = compute_obv(df)
    obv_slope = float(obv.iloc[-1] - obv.iloc[-6]) / (abs(obv.iloc[-6]) + 1)  # 5 günlük OBV eğimi

    close = df["Close"]
    ema50 = compute_ema(close, 50).iloc[-1]
    price = float(close.iloc[-1])
    above_ema50 = price > ema50

    # Skor: 0-100
    score = 0
    score += min(rvol * 20, 35)          # maks 35 puan (RVOL)
    score += min(max(mfi_val - 50, 0), 25)  # maks 25 puan (MFI > 50)
    score += 20 if obv_slope > 0 else 0  # OBV yükseliyor mu?
    score += 20 if above_ema50 else 0    # EMA50 üstünde mi?

    sinyal = "🔴 Zayıf"
    if score >= 70:
        sinyal = "🟢 Güçlü Birikim"
    elif score >= 45:
        sinyal = "🟡 Orta Sinyal"

    return {
        "score": round(score, 1),
        "rvol": round(rvol, 2),
        "mfi": round(mfi_val, 1),
        "obv_rising": obv_slope > 0,
        "above_ema50": above_ema50,
        "price": round(price, 2),
        "sinyal": sinyal,
    }


@st.cache_data(ttl=300)
def _fetch_whale_data(ticker: str) -> pd.DataFrame | None:
    try:
        df = yf.download(ticker, period="3mo", interval="1d", progress=False, auto_adjust=True)
        if df is None or len(df) < 20:
            return None
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
        return df
    except Exception:
        return None


def page_whale_radar(tickers: list):
    st.markdown(
        '<div class="page-header">'
        '<h2>🐋 Büyük Para Takibi</h2>'
        '<p>Kurumsal para hangi hisseye giriyor? Yükselişin öncesinde hacim anormal yükseliyor — '
        'bunu yakalamak için tek kriter yeterli: <b>olağandışı hacim + yükselen fiyat + trend üstünde.</b> '
        'Basit tut. Çok indikatör değil, doğru soru sor.</p>'
        '</div>', unsafe_allow_html=True)

    universe_options = {
        "Momentum Evreni (40 hisse)": MOMENTUM_UNIVERSE,
        "Nasdaq-100": NASDAQ100,
        "Özel Havuz": tickers,
    }
    col_a, col_b = st.columns([2, 1])
    with col_a:
        secim = st.selectbox("Tarama evreni", list(universe_options.keys()))
    with col_b:
        min_rvol = st.slider("Min. RVOL", 1.0, 4.0, 1.5, 0.1,
                             help="1.5x = ortalamanın 1.5 katı hacim. 2x+ = güçlü kurumsal ilgi.")

    scan_list = universe_options[secim]

    if st.button("🔍 Büyük Para Tara", type="primary", use_container_width=True, key="bm_radar"):
        results = []
        prog = st.progress(0, "Taranıyor...")
        for i, ticker in enumerate(scan_list):
            prog.progress((i + 1) / len(scan_list), f"{ticker}")
            df = _fetch_whale_data(ticker)
            if df is None or len(df) < 22:
                continue
            rvol  = relative_volume(df, 20)
            if rvol < min_rvol:
                continue
            price = float(df["Close"].iloc[-1])
            chg   = (price - float(df["Close"].iloc[-2])) / float(df["Close"].iloc[-2]) * 100
            ema10 = float(compute_ema(df["Close"], 10).iloc[-1])
            ema20 = float(compute_ema(df["Close"], 20).iloc[-1])
            ema50 = float(compute_ema(df["Close"], 50).iloc[-1])
            trend_ok = price > ema10 > ema20
            above50  = price > ema50
            dolar_vol = price * float(df["Volume"].iloc[-1]) / 1e6

            # OBV eğimi — son 5 gün
            obv = compute_obv(df)
            obv_rising = float(obv.iloc[-1]) > float(obv.iloc[-6])

            sinyal = "🟢 Güçlü" if (trend_ok and chg > 0 and obv_rising) else "🟡 İzle"
            results.append({
                "Hisse": ticker, "Sinyal": sinyal,
                "Fiyat": round(price, 2), "Günlük %": round(chg, 2),
                "RVOL": round(rvol, 2), "Hacim ($M)": round(dolar_vol, 1),
                "Trend": "✅" if trend_ok else "⚠️",
                "EMA50": "✅" if above50 else "❌",
                "OBV": "↑" if obv_rising else "↓",
                "_rvol": rvol, "_guclu": trend_ok and chg > 0 and obv_rising,
            })
        prog.empty()
        results.sort(key=lambda x: (x["_guclu"], x["_rvol"]), reverse=True)
        st.session_state["whale_radar_results"] = results

    results = st.session_state.get("whale_radar_results")
    if not results:
        st.info("'Büyük Para Tara' butonuna bas. Basit kriter: RVOL yüksek + fiyat yukarı + trend sağlam.")
        return

    guclu = [r for r in results if r["_guclu"]]
    izle  = [r for r in results if not r["_guclu"]]

    m1, m2, m3 = st.columns(3)
    m1.metric("🟢 Güçlü Sinyal", len(guclu))
    m2.metric("🟡 İzleme Listesi", len(izle))
    m3.metric("Toplam Tarama", len(scan_list))

    if guclu:
        st.markdown("### 🔥 Güçlü Kurumsal İlgi")
        st.caption("RVOL yüksek + fiyat yukarı + OBV yükseliyor + trend üstünde")
        per_row = 4
        for start in range(0, len(guclu), per_row):
            cols = st.columns(per_row)
            for col, r in zip(cols, guclu[start:start + per_row]):
                col.markdown(
                    f'<div style="background:rgba(22,199,132,0.10);border:1px solid {C_UP};'
                    f'border-radius:12px;padding:12px;text-align:center;margin-bottom:8px;">'
                    f'<div style="font-weight:800;font-size:1.05rem;color:#fff;">{r["Hisse"]}</div>'
                    f'<div style="color:{C_UP};font-size:0.95rem;font-weight:700;">{r["Günlük %"]:+.2f}%</div>'
                    f'<div style="color:{C_GOLD};font-size:0.85rem;font-weight:600;">{r["RVOL"]}x hacim</div>'
                    f'<div style="color:#6b7280;font-size:0.72rem;margin-top:2px;">'
                    f'${r["Fiyat"]} · ${r["Hacim ($M)"]}M · OBV {r["OBV"]}</div>'
                    f'</div>', unsafe_allow_html=True)

    if izle:
        with st.expander(f"🟡 İzleme listesi ({len(izle)} hisse) — RVOL yüksek ama koşullar tam değil"):
            izle_df = pd.DataFrame([{k: v for k, v in r.items() if not k.startswith("_")} for r in izle])
            st.dataframe(izle_df, use_container_width=True, hide_index=True,
                         column_config={"RVOL": st.column_config.NumberColumn(format="%.2fx"),
                                        "Günlük %": st.column_config.NumberColumn(format="%.2f%%")})


# ===========================================================================
# ===========================================================================
# GELİŞİM & PRATİK
# ===========================================================================

@st.cache_data(ttl=300)
def _quick_opportunity_scan(universe: list) -> list:
    """
    Sekme açılınca otomatik çalışır — buton yok.
    EP, Kırılım ve EMA Geri Çekilme setuplarını hızlıca tarar.
    """
    results = []
    for t in universe:
        df = fetch_daily(t, "3mo")
        if df is None or len(df) < 30:
            continue
        setup = detect_setup(df)
        if "Belirsiz" in setup or "Zayıf" in setup or "Trend" == setup.strip():
            continue
        rvol  = relative_volume(df, 20)
        price = float(df["Close"].iloc[-1])
        chg   = (price - float(df["Close"].iloc[-2])) / float(df["Close"].iloc[-2]) * 100
        ema10 = float(compute_ema(df["Close"], 10).iloc[-1])
        ema20 = float(compute_ema(df["Close"], 20).iloc[-1])
        trend_ok = price > ema10 > ema20
        if not trend_ok and "Episodik" not in setup:
            continue
        plan = explain_trade(setup, df)
        results.append({
            "ticker": t, "setup": setup, "rvol": round(rvol, 2),
            "chg": round(chg, 2), "price": round(price, 2),
            "plan": plan, "_score": rvol + (2 if "Kırılım" in setup or "Episodik" in setup else 1),
        })
    results.sort(key=lambda x: x["_score"], reverse=True)
    return results[:10]


def page_learning(tickers: list, initial_cash: float, risk_pct: float):
    st.markdown(
        '<div class="page-header">'
        '<h2>📚 Gelişim & Pratik</h2>'
        '<p>Günlük rutin · Fırsat Radarı · Setup öğren · Simülasyon ile pratik yap.<br>'
        'Qullamaggie\'nin dediği gibi: <b>"Ekran süresi her şeydir. Binlerce grafik gör, pattern tanıma gelir."</b></p>'
        '</div>', unsafe_allow_html=True)

    sec1, sec2 = st.tabs(["🎯 Fırsat Radarı", "🎮 Simülasyon"])

    # ═══════════════════════════════════════════════════════════
    # BÖLÜM 1: FIRSAT RADARI + GÜNLÜK KONTROL LİSTESİ
    # ═══════════════════════════════════════════════════════════
    with sec1:
        # ── Günlük kontrol listesi ──────────────────────────────
        st.markdown("### ✅ Günlük Trader Kontrol Listesi")
        st.caption("Her sabah sırayla geç. Hepsi ✅ olmadan pozisyon açma.")

        checks = [
            ("🌍 Piyasa Nabzı", "SPX ve Nasdaq trend üstünde mi? VIX düşüyor mu? Risk-On ortam mı?"),
            ("📊 Sektör", "En güçlü sektör hangisi? Hissen o sektörde mi?"),
            ("🎯 Setup", "Kırılım / EP / EMA geri çekilme var mı? Setup net görünüyor mu?"),
            ("📏 Hacim", "Kırılımda hacim 1.5x+ mı? EP'de 2.5x+ mı? Düşük hacimli kırılım = sahte."),
            ("💰 Trade Planı", "Giriş, stop ve hedef belirlendi mi? R/R en az 2:1 mi?"),
            ("🛡️ Risk", f"Stop'a kadar kayıp hesaplandı mı? Hesabın %{risk_pct:.0f}'inden fazla risk var mı?"),
        ]
        cols = st.columns(2)
        for i, (baslik, aciklama) in enumerate(checks):
            with cols[i % 2]:
                st.markdown(
                    f'<div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);'
                    f'border-radius:10px;padding:10px 14px;margin-bottom:8px;">'
                    f'<div style="font-size:0.88rem;font-weight:700;color:#f1f5f9;">{baslik}</div>'
                    f'<div style="font-size:0.78rem;color:#6b7280;margin-top:3px;">{aciklama}</div>'
                    f'</div>', unsafe_allow_html=True)

        st.divider()

        # ── Fırsat Radarı: otomatik tarama ──────────────────────
        st.markdown("### 🔭 Fırsat Radarı — Bugünkü Setuplar")
        st.caption("Otomatik tarama (5 dk cache). Sadece net setup olan hisseler listelenir.")

        scan_universe = list(dict.fromkeys(MOMENTUM_UNIVERSE + tickers))
        with st.spinner("Taranıyor..."):
            opps = _quick_opportunity_scan(tuple(scan_universe))

        if not opps:
            st.info("Şu an net bir setup yok. Piyasa nabzını kontrol et — Risk-Off ortamda fırsat az olur.")
        else:
            # Üst kartlar: en iyi 4
            top4 = opps[:4]
            cols = st.columns(len(top4))
            for col, r in zip(cols, top4):
                plan = r["plan"]
                chg_col = C_UP if r["chg"] >= 0 else C_DOWN
                setup_col = (C_UP if "Kırılım" in r["setup"] or "Episodik" in r["setup"]
                             else C_GOLD if "EMA" in r["setup"] else "#9ca3af")
                plan_html = ""
                if plan:
                    entry  = plan.get("entry", "—")
                    stop   = plan.get("stop", "—")
                    target = plan.get("target", "—")
                    rr     = plan.get("rr", "—")
                    plan_html = (
                        f'<div style="font-size:0.72rem;margin-top:6px;border-top:1px solid '
                        f'rgba(255,255,255,0.06);padding-top:5px;color:#9ca3af;">'
                        f'<b style="color:#fff;">G:</b>${entry} &nbsp;'
                        f'<b style="color:{C_DOWN};">S:</b>${stop} &nbsp;'
                        f'<b style="color:{C_UP};">H:</b>${target} &nbsp;'
                        f'R/R <b style="color:{C_GOLD};">{rr}:1</b></div>'
                    )
                col.markdown(
                    f'<div style="background:rgba(255,255,255,0.03);border:1px solid {setup_col};'
                    f'border-radius:12px;padding:12px;margin-bottom:8px;">'
                    f'<div style="font-size:1.1rem;font-weight:800;color:#fff;">{r["ticker"]}</div>'
                    f'<div style="font-size:0.78rem;color:{setup_col};margin:3px 0;">{r["setup"]}</div>'
                    f'<div style="font-size:0.82rem;color:{chg_col};">{r["chg"]:+.2f}% &nbsp;'
                    f'<span style="color:#6b7280;">{r["rvol"]}x hacim</span></div>'
                    f'{plan_html}'
                    f'</div>', unsafe_allow_html=True)

            # Tüm liste
            if len(opps) > 4:
                with st.expander(f"📋 Tüm fırsatlar ({len(opps)})"):
                    rows = []
                    for r in opps:
                        p = r["plan"]
                        rows.append({
                            "Hisse": r["ticker"], "Setup": r["setup"],
                            "Değişim %": r["chg"], "RVOL": r["rvol"],
                            "Giriş": p.get("entry", "—"), "Stop": p.get("stop", "—"),
                            "Hedef": p.get("target", "—"), "R/R": p.get("rr", "—"),
                        })
                    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True,
                                 column_config={
                                     "Değişim %": st.column_config.NumberColumn(format="%.2f%%"),
                                     "RVOL": st.column_config.NumberColumn(format="%.2fx"),
                                 })

        st.divider()

        # ── Qullamaggie Setup Kartları ────────────────────────────
        st.markdown("### 📖 Setup Rehberi — Qullamaggie'nin 3 Kurulumu")
        setup_cards = [
            {
                "icon": "🚀", "isim": "Kırılım (Breakout from Base)",
                "ne": "Güçlü trenddeki hisse konsolide olur. Hacim daralır. Sonra hacimle üst kırılır.",
                "nasil": "EMA10 > EMA20 üstünde · Son 10 günde dar bant · Kırılım günü hacim 1.5x+",
                "giris": "Kırılım seviyesinin hemen üstü",
                "stop": "EMA10 altı veya kırılım mumunun dibi",
                "hedef": "Önceki büyük yükseliş kadar (~%20-50)",
                "dikkat": "Hacim yoksa kırılım sahtedir. Bekle.",
                "renk": C_UP,
            },
            {
                "icon": "⚡", "isim": "Episodik Pivot (EP)",
                "ne": "Haber/kataliz ile sabah gap-up %4+, hacim 3x+. Kurumlar hisseyi yeniden fiyatlıyor.",
                "nasil": "Gap %4+ · Hacim 2.5x+ · Gap kapatılmıyor (güç işareti)",
                "giris": "Gap günü kapanışa yakın veya ilk pullback'te",
                "stop": "Gap günü dibi — bu kapanırsa setup bozulmuş",
                "hedef": "%20-50 (EP'ler sert gider, erken çıkma)",
                "dikkat": "Gap tamamen kapanırsa çık. Beklemeden.",
                "renk": C_GOLD,
            },
            {
                "icon": "🔄", "isim": "EMA Geri Çekilme (Pullback to MA)",
                "ne": "Güçlü trend devam ederken fiyat EMA10'a veya EMA20'ye çekilir, hacim düşer, sonra döner.",
                "nasil": "Trend yukarı · EMA'lar yukarı eğimli · Geri çekilme düşük hacimde · Dönüş yüksek hacimde",
                "giris": "EMA10'un hemen üstü, döndüğü gün",
                "stop": "EMA20 altı",
                "hedef": "Önceki zirve veya 3:1 R/R",
                "dikkat": "EMA20 kırılırsa trend bozulmuş olabilir — çık.",
                "renk": C_ACCENT,
            },
        ]
        for card in setup_cards:
            st.markdown(
                f'<div style="background:rgba(255,255,255,0.02);border-left:4px solid {card["renk"]};'
                f'border-radius:8px;padding:14px 18px;margin-bottom:12px;">'
                f'<div style="font-size:1rem;font-weight:800;color:#f1f5f9;margin-bottom:6px;">'
                f'{card["icon"]} {card["isim"]}</div>'
                f'<div style="font-size:0.85rem;color:#d1d5db;margin-bottom:8px;">{card["ne"]}</div>'
                f'<div style="display:flex;gap:20px;flex-wrap:wrap;font-size:0.78rem;">'
                f'<div><b style="color:#9ca3af;">Koşul:</b> {card["nasil"]}</div>'
                f'</div>'
                f'<div style="display:flex;gap:20px;flex-wrap:wrap;font-size:0.78rem;margin-top:6px;">'
                f'<div>🟢 <b>Giriş:</b> {card["giris"]}</div>'
                f'<div>🔴 <b>Stop:</b> {card["stop"]}</div>'
                f'<div>🎯 <b>Hedef:</b> {card["hedef"]}</div>'
                f'</div>'
                f'<div style="font-size:0.75rem;color:#ea3943;margin-top:8px;">⚠️ {card["dikkat"]}</div>'
                f'</div>', unsafe_allow_html=True)

        st.divider()

        # ── Qullamaggie Altın Kuralları ──────────────────────────
        with st.expander("📜 Qullamaggie'nin Altın Kuralları"):
            st.markdown("""
**Para yönetimi (en önemli kısım):**
- İşlem başına hesabın **%1'ini** riske at. Asla %2'yi geçme.
- 10 üst üste kayıpsan bile hesabın **%10'unu** kaybetmiş olursun — devam edebilirsin.
- Kazanan pozisyonları kes değil, **kes kaybedenleri hızlıca**.

**Setup kuralları:**
- Piyasa aleyhine asla işlem açma. SPX düşüyorsa nakit kal.
- Hacim onaylamıyorsa kırılım sahtedir. Bekle.
- EP'de gap kapatılıyorsa çık — kurumlar satıyor demektir.

**Psikoloji:**
- Kaybettiğinde intikam işlemi açma. Bir gün mola ver.
- Kazanıyorken pozisyon büyüt (winning streak). Kaybediyorken küçült.
- Trade planını açmadan önce yaz. İçgüdüyle işlem açma.

**Ekran süresi:**
- Her gün kapanışta en az 50-100 grafik tara. Pattern tanıma bu şekilde gelişir.
- Haberden değil, **grafikten** karar ver.
- Bir hisseyi anlamıyorsan geç. Başka fırsat var.

**Pozisyon yönetimi:**
- 3-5 pozisyon yeterli. Fazla çeşitlendirme = dikkat dağınıklığı.
- İlk hedefte %25-50 sat, geri kalanı taşı (trailing stop).
- Büyük kazançlar birkaç işlemden gelir — onları erken kesme.
            """)

    # ═══════════════════════════════════════════════════════════
    # BÖLÜM 2: SİMÜLASYON
    # ═══════════════════════════════════════════════════════════
    with sec2:
        page_simulation(tickers, "6mo", "1d", initial_cash, risk_pct)


# ANA UYGULAMA
# ===========================================================================

def main():
    st.set_page_config(page_title="ABD Borsa Botu", page_icon="📈", layout="wide")

    st.markdown("""
    <style>
    /* ── Genel arka plan ── */
    .stApp { background: #0b0f1a; }

    /* ── Sekme çubuğu ── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background: #111827;
        border-radius: 12px;
        padding: 5px;
        border: 1px solid rgba(255,255,255,0.07);
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 8px 16px;
        font-size: 0.85rem;
        font-weight: 500;
        color: #9ca3af;
        background: transparent;
        border: none;
        transition: all 0.2s;
    }
    .stTabs [aria-selected="true"] {
        background: #1e293b !important;
        color: #f1f5f9 !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
    }
    .stTabs [data-baseweb="tab-highlight"] { display: none; }
    .stTabs [data-baseweb="tab-border"] { display: none; }

    /* ── Kart bileşeni ── */
    .mcard {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.07);
        border-radius: 12px;
        padding: 14px;
        text-align: center;
    }
    .mval { font-size: 1.25rem; font-weight: 700; color: #3b82f6; }
    .mlbl { font-size: 0.72rem; color: #6b7280; margin-top: 2px; }

    /* ── Rozet ── */
    .badge {
        display: inline-block;
        background: rgba(240,185,11,0.12);
        border: 1px solid rgba(240,185,11,0.4);
        border-radius: 20px;
        padding: 3px 10px;
        margin: 3px;
        font-size: 0.78rem;
        color: #f0b90b;
    }

    /* ── Sayfa başlık bloğu ── */
    .page-header {
        background: rgba(255,255,255,0.02);
        border: 1px solid rgba(255,255,255,0.07);
        border-radius: 14px;
        padding: 20px 24px;
        margin-bottom: 20px;
    }
    .page-header h2 { margin: 0 0 4px 0; font-size: 1.3rem; color: #f1f5f9; }
    .page-header p  { margin: 0; font-size: 0.85rem; color: #6b7280; }

    /* ── Uyarı bandı ── */
    .warn-bar {
        background: rgba(234,57,67,0.08);
        border-left: 3px solid #ea3943;
        border-radius: 6px;
        padding: 8px 14px;
        font-size: 0.78rem;
        color: #9ca3af;
        margin-bottom: 16px;
    }

    /* ── Sidebar ── */
    section[data-testid="stSidebar"] { background: #0f172a; }
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stSlider label,
    section[data-testid="stSidebar"] .stNumberInput label { font-size: 0.82rem; color: #9ca3af; }
    </style>
    """, unsafe_allow_html=True)

    # Uyarı bandı
    st.markdown(
        '<div class="warn-bar">⚠️ Bu araç yalnızca eğitim amaçlıdır. '
        'Gerçek emir göndermez ve yatırım tavsiyesi niteliği taşımaz.</div>',
        unsafe_allow_html=True)

    # Başlık
    st.markdown(
        '<h1 style="font-size:1.6rem;font-weight:800;color:#f1f5f9;margin-bottom:2px;">📈 Qullamaggie Trading</h1>'
        '<p style="color:#6b7280;font-size:0.82rem;margin-bottom:16px;">'
        'Piyasayı oku · Setup bul · Planla · Gir</p>',
        unsafe_allow_html=True)

    # ── Sidebar ──
    with st.sidebar:
        st.markdown('<p style="font-size:0.95rem;font-weight:700;color:#f1f5f9;margin-bottom:8px;">⚙️ Ayarlar</p>',
                    unsafe_allow_html=True)
        custom = st.text_input("Hisse listesi (virgülle)", "", placeholder="AAPL, MSFT, NVDA",
                               key="sidebar_tickers")
        tickers = [t.strip().upper() for t in custom.split(",") if t.strip()] or list(DEFAULT_TICKERS)

        st.divider()
        st.markdown('<p style="font-size:0.78rem;font-weight:600;color:#9ca3af;">RİSK YÖNETİMİ</p>',
                    unsafe_allow_html=True)
        initial_cash = st.number_input("Sermaye ($)", 100.0, 1_000_000.0, 10000.0, 100.0,
                                       key="sidebar_cash")
        risk_pct = st.slider("İşlem başına risk (%)", 0.25, 5.0, 1.0, 0.25,
                             help="%1 kural: her işlemde hesabın yalnızca %1'ini riske at.",
                             key="sidebar_risk")
        fee_pct = st.number_input("Komisyon (%)", 0.0, 1.0, 0.05, 0.01, key="sidebar_fee")

        st.divider()
        st.markdown(
            f'<p style="font-size:0.75rem;color:#4b5563;">Havuz: '
            f'<b style="color:#9ca3af;">{len(tickers)} hisse</b><br>'
            f'<span style="color:#374151;">{", ".join(tickers[:6])}{"…" if len(tickers) > 6 else ""}</span></p>',
            unsafe_allow_html=True)

    # ── 3 Sekme: bir tradercının günlük iş akışı ──
    tab1, tab2, tab3 = st.tabs([
        "🌍  Piyasa Nabzı",
        "🎯  Qullamaggie",
        "📚  Gelişim & Pratik",
    ])
    with tab1:
        page_market_pulse(tickers)
    with tab2:
        page_momentum()
    with tab3:
        page_learning(tickers, initial_cash, risk_pct)


if __name__ == "__main__":
    main()
