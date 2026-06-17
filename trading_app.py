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
    "^DJI": "Dow Jones",
    "^RUT": "Russell 2000",
    "^VIX": "VIX (Korku)",
    "^TNX": "10Y Faiz",
    "DX-Y.NYB": "Dolar (DXY)",
    "GC=F": "Altın",
    "CL=F": "Petrol",
    "BTC-USD": "Bitcoin",
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
    """Mum yapısına göre setup etiketi (bayrak / kırılım / trend)."""
    c = df["Close"]
    if len(c) < 25:
        return "Yetersiz veri"
    ema10, ema20 = compute_ema(c, 10), compute_ema(c, 20)
    price = float(c.iloc[-1])
    above_cloud = price > ema10.iloc[-1] > ema20.iloc[-1]

    # Son 10 mumun sıkışması (bayrak): dar aralık + bulut üstü
    recent = c.iloc[-10:]
    rng = (recent.max() - recent.min()) / recent.min() * 100
    adr = compute_adr_pct(df)
    cons_high = float(df["High"].iloc[-11:-1].max())
    vol_now = df["Volume"].iloc[-1]
    vol_avg = df["Volume"].iloc[-20:].mean()

    if above_cloud and price > cons_high and vol_now > vol_avg * 1.3:
        return "🚀 Kırılım (Breakout)"
    if above_cloud and rng < adr * 2.2:
        return "🏴 Bayrak / Sıkışma"
    if above_cloud:
        return "📈 Trend (bulut üstü)"
    if price < ema20.iloc[-1]:
        return "⚠️ Bulut altı (zayıf)"
    return "↔️ Belirsiz"


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
    st.subheader("📡 Piyasa Tarayıcı")
    st.caption("Tüm hisse havuzu UT Bot mantığıyla taranır. AL/SAT sinyali verenler ve eğilim adayları gruplanır.")

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
    st.subheader("🤖 Detaylı Hisse Analizi")
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
        tt = trend_template(df)
        adr = compute_adr_pct(df)
        rs = int(round(scores[t]))
        setup = detect_setup(df)
        chg = (df["Close"].iloc[-1] - df["Close"].iloc[-2]) / df["Close"].iloc[-2] * 100
        rvol = relative_volume(df)
        rows.append({
            "Hisse": t,
            "Setup": setup,
            "RS": rs,
            "ADR %": round(adr, 1),
            "Trend": f"{tt['passed']}/{tt['total']}",
            "Zirveye %": tt["pct_from_high"],
            "Gör. Hacim": round(rvol, 2),
            "Günlük %": round(float(chg), 2),
            "Fiyat": round(float(df["Close"].iloc[-1]), 2),
            "_pass": tt["passed"], "_adr": adr, "_rs": rs,
            "_above": tt["above_cloud"] and tt["above_50"],
        })
    prog.empty()
    df = pd.DataFrame(rows)
    # Filtre: RS ve ADR eşiği + trend yapısı sağlam
    df = df[(df["_rs"] >= min_rs) & (df["_adr"] >= min_adr) & (df["_above"])]
    return df.sort_values(["_pass", "_rs"], ascending=False)


def page_momentum():
    st.subheader("🚀 Momentum / Breakout Tarayıcı")
    st.caption("Qullamaggie & Minervini tarzı: güçlü momentum (yüksek RS) + yüksek ADR% + "
               "EMA bulutu üstünde sıkışma/kırılım. Tıpkı FCEL, ARM, FLNC tarzı kurulumlar.")

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
        return
    if df.empty:
        st.warning("Bu filtrelerle eşleşen hisse yok. RS/ADR eşiğini düşürmeyi dene.")
        return

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
                     "RS": st.column_config.ProgressColumn(min_value=0, max_value=99, format="%d"),
                     "Günlük %": st.column_config.NumberColumn(format="%.2f%%"),
                     "Zirveye %": st.column_config.NumberColumn(format="%.1f%%"),
                 })

    st.divider()
    # Seçili hissenin bulut grafiği
    pick = st.selectbox("📈 Grafiğini gör (EMA bulutu)", show["Hisse"].tolist())
    if pick:
        cdf = fetch_daily(pick, "1y")
        if cdf is not None:
            st.plotly_chart(make_cloud_chart(cdf, f"{pick} • 10/20 EMA Bulut + 50/200 SMA"),
                            use_container_width=True)

    with st.expander("📚 Bu sistem nasıl çalışır?"):
        st.markdown("""
**Qullamaggie / Minervini Momentum Breakout sistemi:**

1. **Güçlü momentum (RS Rating):** Hisse son aylarda piyasadan çok daha fazla yükselmiş olmalı.
   RS 80-99 = en güçlü %20'lik dilim. Lider hisseleri seçmek için ilk filtre.
2. **Yüksek ADR%:** Günlük ortalama hareket aralığı. Yüksek ADR = daha çok hareket = daha çok fırsat.
   Qullamaggie genelde **%5+** arar.
3. **EMA Bulutu (10/20):** Fiyat bulutun üstündeyse trend sağlam. Geri çekilmeler buluta kadardır.
4. **Trend Template (Minervini):** Fiyat > 50MA > 150MA > 200MA, 200MA yukarı, zirveye yakın.
5. **Setup:**
   - **🏴 Bayrak/Sıkışma:** Büyük yükseliş sonrası bulut üstünde dar konsolidasyon.
   - **🚀 Kırılım:** Konsolidasyon tepesini (veya düşen trend çizgisini) **hacimle** kırması = alım tetiği.
6. **Stop:** Genelde kırılım mumunun dibi veya 10/20 EMA bulutunun altı.

**Önemli:** RS Rating burada *havuz içi* yüzdelik sıralamadır (gerçek IBD tüm borsayı kapsar).
Listeyi büyüttükçe RS daha anlamlı olur.
        """)


def _build_daily_summary(spx_chg, vix_chg, sec_df, wdf) -> str:
    """Makro + sektör + para akışını tek paragrafta özetler."""
    tarih = datetime.now().strftime("%d.%m.%Y")
    parts = [f"**{tarih} piyasa görünümü:**", ""]

    # Risk iştahı
    if spx_chg > 0 and vix_chg < 0:
        parts.append(f"- 🟢 **Risk-On ortam.** S&P 500 **{spx_chg:+.2f}%**, korku endeksi VIX **{vix_chg:+.2f}%**. "
                     "Piyasa iştahlı; trend yönünde (long) kurulumlar daha güvenli.")
    elif spx_chg < 0 and vix_chg > 0:
        parts.append(f"- 🔴 **Risk-Off ortam.** S&P 500 **{spx_chg:+.2f}%**, VIX **{vix_chg:+.2f}%** yükseldi. "
                     "Temkinli ol; pozisyonları küçült, savunma sektörlerine bak.")
    else:
        parts.append(f"- 🟡 **Karışık ortam.** S&P 500 **{spx_chg:+.2f}%**, VIX **{vix_chg:+.2f}%**. "
                     "Net yön yok; seçici ol ve teyit bekle.")

    # Sektör rotasyonu
    if sec_df is not None and not sec_df.empty:
        best, worst = sec_df.iloc[0], sec_df.iloc[-1]
        parts.append(f"- 💰 **Para girişi:** {best['Sektör']} (haftalık {best['Haftalık %']:+.2f}%). "
                     f"💸 **Para çıkışı:** {worst['Sektör']} (haftalık {worst['Haftalık %']:+.2f}%). "
                     f"Güçlü sektördeki güçlü hisseler önceliklidir.")

    # Balina / para akışı
    if wdf is not None and not wdf.empty:
        acc = wdf[wdf["Durum"].str.contains("Birikim")]
        dist = wdf[wdf["Durum"].str.contains("Dağıtım")]
        unusual = wdf[wdf["Durum"].str.contains("Olağandışı")]
        if not acc.empty:
            isimler = ", ".join(acc.sort_values("Göreli Hacim", ascending=False)["Hisse"].head(4))
            parts.append(f"- 🐋 **Birikim (alıcı baskısı):** {isimler}.")
        if not dist.empty:
            isimler = ", ".join(dist.sort_values("Göreli Hacim", ascending=False)["Hisse"].head(4))
            parts.append(f"- 📉 **Dağıtım (satıcı baskısı):** {isimler}.")
        if not unusual.empty:
            isimler = ", ".join(unusual.sort_values("Göreli Hacim", ascending=False)["Hisse"].head(4))
            parts.append(f"- ⚡ **Olağandışı hacim:** {isimler}.")
    else:
        parts.append("- 🐋 Para akışı detayı için yukarıdan **'Para Akışını Tara'** butonuna bas.")

    parts.append("")
    parts.append("> Bu özet otomatik üretildi, yatırım tavsiyesi değildir.")
    return "\n".join(parts)


def page_market_pulse(tickers):
    st.subheader("🐋 Piyasa Nabzı — Makro, Sektör Rotasyonu & Para Akışı")
    top = st.columns([3, 1])
    top[0].caption("Veri ~15 dk gecikmeli (Yahoo Finance). 'Yenile' ile güncelle veya cache 3 dk'da otomatik tazelenir.")
    if top[1].button("🔄 Yenile", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.caption(f"Son güncelleme: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")

    # ---------- 1) MAKRO TABLO ----------
    st.markdown("### 🌍 Günlük Makro Özet")
    macro_rows, spx_chg, vix_chg = [], 0, 0
    for sym, name in MACRO_ASSETS.items():
        df = fetch_daily(sym, "5d")
        if df is None or len(df) < 2:
            continue
        chg = (df["Close"].iloc[-1] - df["Close"].iloc[-2]) / df["Close"].iloc[-2] * 100
        if sym == "^GSPC": spx_chg = chg
        if sym == "^VIX": vix_chg = chg
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

    # ---------- 3) BALİNA / PARA AKIŞI RADARI ----------
    st.markdown("### 🐋 Balina & Olağandışı Hacim Radarı")
    st.caption("Hisse havuzunda kurumsal/balina aktivitesi vekil göstergelerle taranır.")
    if st.button("🔍 Para Akışını Tara", type="primary", use_container_width=True):
        st.session_state["whale_scan"] = detect_whale_activity(tickers)

    wdf = st.session_state.get("whale_scan")
    if wdf is not None and not wdf.empty:
        acc = wdf[wdf["Durum"].str.contains("Birikim")].sort_values("Göreli Hacim", ascending=False)
        dist = wdf[wdf["Durum"].str.contains("Dağıtım")].sort_values("Göreli Hacim", ascending=False)
        unusual = wdf[wdf["Durum"].str.contains("Olağandışı")].sort_values("Göreli Hacim", ascending=False)

        cc = st.columns(3)
        cc[0].metric("🐋 Birikim", len(acc))
        cc[1].metric("📉 Dağıtım", len(dist))
        cc[2].metric("⚡ Olağandışı Hacim", len(unusual))

        st.dataframe(
            wdf.sort_values("Göreli Hacim", ascending=False),
            use_container_width=True, hide_index=True,
            column_config={
                "Göreli Hacim": st.column_config.NumberColumn(format="%.2fx",
                    help="Bugünkü hacim / 20 gün ort. >1.5 olağandışı, >2 güçlü ilgi"),
                "Günlük %": st.column_config.NumberColumn(format="%.2f%%"),
                "MFI": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%d"),
            })

    # ---------- 4) GÜNÜN OTOMATİK ÖZETİ ----------
    st.divider()
    st.markdown("### 📋 Günün Özeti")
    st.markdown(_build_daily_summary(spx_chg, vix_chg, sec_df, st.session_state.get("whale_scan")))

    # ---------- 5) NASIL TESPİT EDİLİR (EĞİTİM) ----------
    with st.expander("📚 Balinaları / para akışını nasıl tespit ederim?"):
        st.markdown("""
**Ücretsiz veriyle kurumsal (balina) aktivitesini bu vekil göstergelerle yakalarsın:**

- **Göreli Hacim (RVOL):** Bugünkü hacim, 20 günlük ortalamanın 1.5–2 katından fazlaysa
  fiyatın arkasında *büyük* bir oyuncu var demektir. Balina girişinin en hızlı işareti budur.
- **MFI (Money Flow Index):** Hacim ağırlıklı RSI. MFI yükselirken fiyat da yükseliyorsa
  **para giriyor (birikim)**; MFI düşerken fiyat düşüyorsa **para çıkıyor (dağıtım)**.
- **OBV (On-Balance Volume):** Hacmi fiyat yönüne göre toplar. OBV fiyattan önce yön
  değiştirirse, kurumlar sessizce topluyor/satıyor olabilir (öncü sinyal).
- **Fiyat + Hacim birlikte:** Güçlü yükseliş + yüksek hacim = gerçek talep. Yükseliş ama
  düşük hacim = zayıf, sürdürülemez.
- **$ Hacim (Dollar Volume):** Fiyat × Hacim. Kurumlar büyük dolar hacimli hisseleri tercih eder.
- **Sektör Rotasyonu:** Para önce sektöre, sonra hisseye gelir. Güçlü sektördeki güçlü hisse en iyisidir.

**Not:** Gerçek dark-pool/blok emir/opsiyon akışı verisi ücretli servis (Unusual Whales vb.)
gerektirir. Buradaki göstergeler bunların halka açık ve güvenilir *vekilleridir*.
        """)


def page_simulation(tickers, period, interval, initial_cash=10000.0, risk_pct=1.0):
    init_sim_state()
    st.session_state["_sim_account"] = initial_cash
    st.session_state["_sim_risk"] = risk_pct
    st.subheader("🎮 Trading Simülasyon Oyunu")
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
# ANA UYGULAMA
# ===========================================================================

def main():
    st.set_page_config(page_title="ABD Al/Sat Botu", page_icon="📈", layout="wide")

    st.markdown("""
    <style>
    .mcard {background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);
            border-radius:12px;padding:10px;text-align:center;}
    .mval {font-size:1.3rem;font-weight:700;color:#3b82f6;}
    .mlbl {font-size:0.72rem;color:#9ca3af;}
    .badge {display:inline-block;background:rgba(240,185,11,0.15);border:1px solid #f0b90b;
            border-radius:20px;padding:3px 10px;margin:3px;font-size:0.8rem;}
    .stTabs [data-baseweb="tab-list"] {gap:8px;}
    .stTabs [data-baseweb="tab"] {border-radius:8px 8px 0 0;padding:8px 18px;}
    </style>
    """, unsafe_allow_html=True)

    st.markdown(
        '<div style="background:rgba(234,57,67,0.1);border-left:3px solid #ea3943;'
        'padding:8px 12px;border-radius:6px;font-size:0.8rem;color:#bbb;margin-bottom:12px;">'
        '⚠️ Yatırım tavsiyesi değildir. Gerçek emir göndermez. Eğitim ve simülasyon amaçlıdır.</div>',
        unsafe_allow_html=True)

    st.title("📈 ABD Borsası Al/Sat Botu")

    with st.sidebar:
        st.title("⚙️ Ayarlar")
        custom = st.text_input("Özel Ticker Listesi (virgülle)", "")
        tickers = [t.strip().upper() for t in custom.split(",") if t.strip()] or list(DEFAULT_TICKERS)
        period_label = st.selectbox("Zaman Aralığı", list(PERIOD_INTERVAL_MAP.keys()), index=2)
        period, interval = PERIOD_INTERVAL_MAP[period_label]
        st.divider()
        st.subheader("UT Bot Parametreleri")
        key_value = st.slider("Key Value (Hassasiyet)", 0.5, 5.0, 1.0, 0.1)
        atr_period = st.slider("ATR Period", 1, 30, 10, 1)
        st.divider()
        st.subheader("Hesap & Risk")
        initial_cash = st.number_input("Hesap / Sermaye ($)", 100.0, 1_000_000.0, 10000.0, 100.0)
        risk_pct = st.slider("İşlem Başına Risk (%)", 0.25, 5.0, 1.0, 0.25,
                             help="Profesyoneller işlem başına hesabın %1-2'sini riske atar.")
        fee_pct = st.number_input("Komisyon (%)", 0.0, 1.0, 0.1, 0.01)
        st.divider()
        st.caption(f"Havuz: {len(tickers)} hisse")
        st.caption(", ".join(tickers[:8]) + ("..." if len(tickers) > 8 else ""))

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["📡 Piyasa Tarayıcı", "🚀 Momentum/Breakout", "🐋 Piyasa Nabzı",
         "🤖 Detaylı Analiz", "🎮 Simülasyon"])
    with tab1:
        page_scanner(tickers, period, interval, key_value, atr_period, initial_cash, risk_pct)
    with tab2:
        page_momentum()
    with tab3:
        page_market_pulse(tickers)
    with tab4:
        page_analysis(tickers, period, interval, key_value, atr_period, initial_cash, fee_pct, risk_pct)
    with tab5:
        page_simulation(tickers, period, interval, initial_cash, risk_pct)


if __name__ == "__main__":
    main()
