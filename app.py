
import os
import time
import math
import json
import threading
from datetime import datetime, timezone, timedelta

import numpy as np
import pandas as pd
import requests
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ============================================================
# AI / TECHNICAL ANALYSIS DASHBOARD
# Candle API + Indicator Engine + Signal Engine + Telegram
#
# Run:
#   pip install -r requirements.txt
#   streamlit run app.py
#
# IMPORTANT:
# This application generates probabilistic technical-analysis
# signals. It does not guarantee the next candle.
# ============================================================

st.set_page_config(
    page_title="Cortex/Quotex AI Signal Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

DEFAULT_API = "https://novexai.org/api.php"
TZ = timezone(timedelta(hours=6))

# The uploaded source specifies M1 candle data, UTC+06:00, and
# a maximum of 1440 candles from the Novex endpoint.
# Source: AI.BOT.txt
OTC_FX = [
    "AUDCAD_otc","AUDCHF_otc","AUDJPY_otc","AUDNZD_otc","AUDUSD_otc",
    "CADCHF_otc","CADJPY_otc","CHFJPY_otc","EURAUD_otc","EURCAD_otc",
    "EURCHF_otc","EURGBP_otc","EURJPY_otc","EURNZD_otc","EURSGD_otc",
    "EURUSD_otc","GBPAUD_otc","GBPCAD_otc","GBPCHF_otc","GBPJPY_otc",
    "GBPNZD_otc","GBPUSD_otc","NZDCAD_otc","NZDCHF_otc","NZDJPY_otc",
    "NZDUSD_otc","USDARS_otc","USDBDT_otc","USDCAD_otc","USDCHF_otc",
    "USDCOP_otc","USDDZD_otc","USDEGP_otc","USDIDR_otc","USDINR_otc",
    "USDJPY_otc","USDMXN_otc","USDNGN_otc","USDPHP_otc","USDPKR_otc",
    "USDTRY_otc","USDZAR_otc"
]
OTC_COMMODITIES = ["UKBrent_otc","USCrude_otc","XAGUSD_otc","XAUUSD_otc"]
OTC_CRYPTO = [
    "ADAUSD_otc","APTUSD_otc","ARBUSD_otc","ATOUSD_otc","AVAUSD_otc",
    "AXSUSD_otc","BCHUSD_otc","BNBUSD_otc","BONUSD_otc","BTCUSD_otc",
    "DASUSD_otc","DOGUSD_otc","DOTUSD_otc","ETCUSD_otc","ETHUSD_otc",
    "FLOUSD_otc","GALUSD_otc","HMSUSD_otc","LINUSD_otc","LTCUSD_otc",
    "MELUSD_otc","SHIUSD_otc","SOLUSD_otc","TIAUSD_otc","TONUSD_otc",
    "TRUUSD_otc","TRXUSD_otc","WIFUSD_otc","XRPUSD_otc","ZECUSD_otc"
]
REAL_FX = [
    "AUDCAD","AUDCHF","AUDJPY","AUDUSD","CADJPY","CHFJPY","EURAUD",
    "EURCAD","EURCHF","EURGBP","EURJPY","EURUSD","GBPAUD","GBPCAD",
    "GBPCHF","GBPJPY","GBPUSD","USDCAD","USDCHF","USDJPY"
]
REAL_COMMODITIES = ["XAGUSD","XAUUSD"]

ALL_PAIRS = OTC_FX + OTC_COMMODITIES + OTC_CRYPTO + REAL_FX + REAL_COMMODITIES

TIMEFRAMES = {
    "1m": 60, "5m": 300, "15m": 900, "30m": 1800,
    "1h": 3600, "2h": 7200, "4h": 14400, "1D": 86400
}

STRATEGIES = [
    "DYNAMIC TOP-N 🧠 (Auto-Switching)",
    "ALL STRATEGIES 🌌",
    "NEURAL STRIKE 🧠 (AI Breakout)",
    "PHANTOM VOLT ⚡ (Volatility)",
    "QUANTUM RIDER 🌀 (Trend Rider)",
    "SHADOW DOJI 🕯️ (Candle Reversal)",
    "VELOCITY BURST 🚀 (Momentum Spikes)",
    "OVERDRIVE RSI 📊 (Extreme RSI)",
    "TITAN CROSS ⚔️ (EMA Crossover)",
    "AETHER CORE 🌌 (FVG Liquidity)",
    "PULSE TREKKER 📈 (ADX Trend Strength)",
    "VORTEX FLOW 🌊 (Volume Trend)",
    "ORBIT EMA 🪐 (Mean Reversion)",
    "ECHO CONFIRM 🔊 (Double Confirmation)",
    "SHIFT MATRIX 🎛️ (HTF S/R Reversal)",
    "VOID WALKER 🕳️ (Gap Filling)",
    "DRAGON TREND 🐉 (Long Trend Ride)",
    "OMEGA EMA 🧬 (Multi-EMA Align)",
    "SILENT STREAM 🤫 (Low Volatility Scalp)",
    "RSI DOMINATOR 👑 (RSI Trend Follow)",
    "GLACIER LOCK 🧊 (Consolidation S/R)",
    "BLACK FILTER X 🖤 (Noise Filter)",
    "CHRONO PATTERN ⏳ (U/V Reversal)",
    "REVERSE NOVA 💥 (Exhaustion Reversal)",
    "BREAKER ALPHA 🛡️ (S/R False Breakout)",
    "SCALP FUSION 🧪 (Quick Scalp)",
    "EMA RAZOR 🪒 (EMA Bounce)",
    "VOLUME REAPER ⚰️ (Volume Absorption)",
    "NOISE KILLER 🔇 (Smoothing Filter)",
    "LONDON VORTEX 🎡 (Session Breakout)",
]

INDICATORS = [
    "EMA 9","EMA 21","EMA 50","EMA 100","EMA 200",
    "SMA 50","SMA 200",
    "RSI","Stochastic RSI","MACD","Momentum Oscillator","CCI",
    "Bollinger Bands","ATR","Keltner Channel","Donchian Channel",
    "OBV","VWAP","MFI","ADX","DMI","Williams %R",
    "Awesome Oscillator","Ultimate Oscillator","Ichimoku",
    "Order Block","Fair Value Gap","Liquidity Zone",
    "Break of Structure","CHOCH","Support & Resistance",
    "Supply & Demand","Pivot Points",
]

# ------------------------------------------------------------
# Utilities
# ------------------------------------------------------------

def safe_float(x, default=np.nan):
    try:
        return float(x)
    except Exception:
        return default

def clamp(x, lo=0.0, hi=100.0):
    if x is None or not np.isfinite(x):
        return lo
    return max(lo, min(hi, float(x)))

def fmt(x, digits=4):
    try:
        if x is None or not np.isfinite(float(x)):
            return "-"
        return f"{float(x):.{digits}f}"
    except Exception:
        return "-"

def last(s):
    if s is None or len(s) == 0:
        return np.nan
    return float(s.iloc[-1]) if hasattr(s, "iloc") else float(s[-1])

def previous(s):
    if s is None or len(s) < 2:
        return np.nan
    return float(s.iloc[-2]) if hasattr(s, "iloc") else float(s[-2])

# ------------------------------------------------------------
# API
# ------------------------------------------------------------

@st.cache_data(ttl=2, show_spinner=False)
def fetch_candles(api_url, pair, count=1440, timeout=12):
    params = {"pair": pair, "count": min(int(count), 1440)}
    r = requests.get(api_url, params=params, timeout=timeout)
    r.raise_for_status()
    payload = r.json()

    if not isinstance(payload, dict):
        raise ValueError("API response is not a JSON object.")
    if payload.get("success") is False:
        raise ValueError(str(payload))

    rows = payload.get("data", [])
    if not rows:
        raise ValueError("API returned no candle data.")

    df = pd.DataFrame(rows)
    required = ["date", "time", "open", "high", "low", "close"]
    missing = [x for x in required if x not in df.columns]
    if missing:
        raise ValueError(f"Missing candle fields: {missing}")

    df["datetime"] = pd.to_datetime(
        df["date"].astype(str) + " " + df["time"].astype(str),
        errors="coerce"
    )
    for c in ["open","high","low","close","volume","payout"]:
        if c in df:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        else:
            df[c] = 0.0

    df = df.dropna(subset=["datetime","open","high","low","close"]).copy()
    df = df.sort_values("datetime").drop_duplicates("datetime").reset_index(drop=True)

    return df, payload

# ------------------------------------------------------------
# Resampling
# ------------------------------------------------------------

def resample_candles(df, timeframe):
    if timeframe == "1m":
        return df.copy()

    rule = {
        "5m":"5min","15m":"15min","30m":"30min",
        "1h":"1h","2h":"2h","4h":"4h","1D":"1D"
    }[timeframe]

    x = df.copy().set_index("datetime")
    out = x.resample(rule, origin="start_day").agg({
        "open":"first",
        "high":"max",
        "low":"min",
        "close":"last",
        "volume":"sum",
        "payout":"last"
    }).dropna(subset=["open","high","low","close"]).reset_index()

    return out

# ------------------------------------------------------------
# Indicator calculations - pure pandas/numpy
# ------------------------------------------------------------

def sma(s, n):
    return s.rolling(n, min_periods=n).mean()

def ema(s, n):
    return s.ewm(span=n, adjust=False, min_periods=n).mean()

def rma(s, n):
    return s.ewm(alpha=1/n, adjust=False, min_periods=n).mean()

def true_range(df):
    pc = df["close"].shift(1)
    return pd.concat([
        df["high"] - df["low"],
        (df["high"] - pc).abs(),
        (df["low"] - pc).abs()
    ], axis=1).max(axis=1)

def atr(df, n=14):
    return rma(true_range(df), n)

def rsi(close, n=14):
    d = close.diff()
    up = d.clip(lower=0)
    dn = -d.clip(upper=0)
    au = rma(up, n)
    ad = rma(dn, n)
    rs = au / ad.replace(0, np.nan)
    out = 100 - (100 / (1 + rs))
    return out.fillna(50)

def macd(close, fast=12, slow=26, signal=9):
    m = ema(close, fast) - ema(close, slow)
    s = ema(m, signal)
    h = m - s
    return m, s, h

def bollinger(close, n=20, mult=2):
    mid = sma(close, n)
    sd = close.rolling(n, min_periods=n).std()
    return mid, mid + mult*sd, mid - mult*sd

def stochastic(df, k=14, d=3):
    lo = df["low"].rolling(k, min_periods=k).min()
    hi = df["high"].rolling(k, min_periods=k).max()
    K = 100 * (df["close"] - lo) / (hi - lo).replace(0, np.nan)
    D = sma(K, d)
    return K.fillna(50), D.fillna(50)

def stochastic_rsi(close, rsi_n=14, stoch_n=14, k=3, d=3):
    R = rsi(close, rsi_n)
    lo = R.rolling(stoch_n, min_periods=stoch_n).min()
    hi = R.rolling(stoch_n, min_periods=stoch_n).max()
    sr = (R - lo) / (hi - lo).replace(0, np.nan)
    K = sma(sr * 100, k)
    D = sma(K, d)
    return K.fillna(50), D.fillna(50)

def cci(df, n=20):
    tp = (df["high"] + df["low"] + df["close"]) / 3
    ma = sma(tp, n)
    md = tp.rolling(n, min_periods=n).apply(
        lambda x: np.mean(np.abs(x - np.mean(x))), raw=True
    )
    return (tp - ma) / (0.015 * md.replace(0, np.nan))

def obv(df):
    direction = np.sign(df["close"].diff()).fillna(0)
    return (direction * df["volume"].fillna(0)).cumsum()

def vwap(df):
    tp = (df["high"] + df["low"] + df["close"]) / 3
    vol = df["volume"].replace(0, np.nan)
    return (tp * vol).cumsum() / vol.cumsum()

def mfi(df, n=14):
    tp = (df["high"] + df["low"] + df["close"]) / 3
    mf = tp * df["volume"].fillna(0)
    sign = np.sign(tp.diff()).fillna(0)
    pos = mf.where(sign > 0, 0).rolling(n, min_periods=n).sum()
    neg = mf.where(sign < 0, 0).abs().rolling(n, min_periods=n).sum()
    ratio = pos / neg.replace(0, np.nan)
    return (100 - 100/(1+ratio)).fillna(50)

def adx_dmi(df, n=14):
    up = df["high"].diff()
    dn = -df["low"].diff()
    plus_dm = up.where((up > dn) & (up > 0), 0.0)
    minus_dm = dn.where((dn > up) & (dn > 0), 0.0)
    tr = true_range(df)
    trn = rma(tr, n)
    plus = 100 * rma(plus_dm, n) / trn.replace(0, np.nan)
    minus = 100 * rma(minus_dm, n) / trn.replace(0, np.nan)
    dx = 100 * (plus - minus).abs() / (plus + minus).replace(0, np.nan)
    adxv = rma(dx, n)
    return adxv.fillna(0), plus.fillna(0), minus.fillna(0)

def williams_r(df, n=14):
    hi = df["high"].rolling(n, min_periods=n).max()
    lo = df["low"].rolling(n, min_periods=n).min()
    return -100 * (hi - df["close"]) / (hi - lo).replace(0, np.nan)

def awesome_oscillator(df):
    median = (df["high"] + df["low"]) / 2
    return sma(median, 5) - sma(median, 34)

def ultimate_oscillator(df):
    pc = df["close"].shift(1)
    bp = df["close"] - pd.concat([df["low"], pc], axis=1).min(axis=1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - pc).abs(),
        (df["low"] - pc).abs()
    ], axis=1).max(axis=1)
    a = bp.rolling(7).sum()/tr.rolling(7).sum().replace(0,np.nan)
    b = bp.rolling(14).sum()/tr.rolling(14).sum().replace(0,np.nan)
    c = bp.rolling(28).sum()/tr.rolling(28).sum().replace(0,np.nan)
    return 100*(4*a + 2*b + c)/7

def ichimoku(df, tenkan=9, kijun=26, senkou=52):
    hi_t = df["high"].rolling(tenkan).max()
    lo_t = df["low"].rolling(tenkan).min()
    ten = (hi_t + lo_t)/2
    hi_k = df["high"].rolling(kijun).max()
    lo_k = df["low"].rolling(kijun).min()
    kij = (hi_k + lo_k)/2
    span_a = (ten + kij)/2
    hi_s = df["high"].rolling(senkou).max()
    lo_s = df["low"].rolling(senkou).min()
    span_b = (hi_s + lo_s)/2
    return ten, kij, span_a, span_b

def keltner(df, n=20, atr_n=10, mult=2):
    mid = ema(df["close"], n)
    a = atr(df, atr_n)
    return mid, mid + mult*a, mid - mult*a

def donchian(df, n=20):
    return df["high"].rolling(n).max(), df["low"].rolling(n).min()

# ------------------------------------------------------------
# Price action / SMC
# ------------------------------------------------------------

def candle_features(df):
    x = df.copy()
    x["body"] = (x["close"] - x["open"]).abs()
    x["range"] = (x["high"] - x["low"]).replace(0, np.nan)
    x["upper_wick"] = x["high"] - x[["open","close"]].max(axis=1)
    x["lower_wick"] = x[["open","close"]].min(axis=1) - x["low"]
    x["green"] = x["close"] > x["open"]
    x["red"] = x["close"] < x["open"]
    x["doji"] = x["body"] <= x["range"] * 0.12
    x["pin_bull"] = (x["lower_wick"] > x["body"]*2) & (x["upper_wick"] < x["body"])
    x["pin_bear"] = (x["upper_wick"] > x["body"]*2) & (x["lower_wick"] < x["body"])
    x["bull_engulf"] = (
        x["green"] &
        (x["open"] <= x["close"].shift(1)) &
        (x["close"] >= x["open"].shift(1)) &
        x["red"].shift(1).fillna(False)
    )
    x["bear_engulf"] = (
        x["red"] &
        (x["open"] >= x["close"].shift(1)) &
        (x["close"] <= x["open"].shift(1)) &
        x["green"].shift(1).fillna(False)
    )
    x["inside_bar"] = (
        (x["high"] < x["high"].shift(1)) &
        (x["low"] > x["low"].shift(1))
    )
    return x

def support_resistance(df, lookback=40):
    recent = df.tail(lookback)
    support = recent["low"].nsmallest(min(5, len(recent))).mean()
    resistance = recent["high"].nlargest(min(5, len(recent))).mean()
    return support, resistance

def pivot_points(df):
    h, l, c = df["high"].iloc[-2], df["low"].iloc[-2], df["close"].iloc[-2]
    p = (h+l+c)/3
    return {
        "P":p, "R1":2*p-l, "S1":2*p-h,
        "R2":p+(h-l), "S2":p-(h-l),
        "R3":h+2*(p-l), "S3":l-2*(h-p)
    }

def market_structure(df, n=3):
    # Swing-high / swing-low based BOS/CHOCH approximation.
    if len(df) < 2*n+5:
        return {"bos":"NONE","choch":"NONE","swing_high":np.nan,"swing_low":np.nan}
    highs = df["high"]
    lows = df["low"]
    swing_highs = highs[(highs.shift(n) < highs) & (highs.shift(-n) < highs)]
    swing_lows = lows[(lows.shift(n) > lows) & (lows.shift(-n) > lows)]
    sh = last(swing_highs.dropna())
    sl = last(swing_lows.dropna())
    close = last(df["close"])
    prev_close = previous(df["close"])
    bos = "BULLISH" if np.isfinite(sh) and close > sh else "BEARISH" if np.isfinite(sl) and close < sl else "NONE"
    choch = "BULLISH" if np.isfinite(sh) and prev_close <= sh < close else "BEARISH" if np.isfinite(sl) and prev_close >= sl > close else "NONE"
    return {"bos":bos,"choch":choch,"swing_high":sh,"swing_low":sl}

def fair_value_gap(df):
    if len(df) < 3:
        return {"bullish":False,"bearish":False,"bull_gap":np.nan,"bear_gap":np.nan}
    a,b,c = df.iloc[-3],df.iloc[-2],df.iloc[-1]
    bull = c["low"] > a["high"]
    bear = c["high"] < a["low"]
    return {
        "bullish":bool(bull),
        "bearish":bool(bear),
        "bull_gap":float(a["high"]) if bull else np.nan,
        "bear_gap":float(a["low"]) if bear else np.nan
    }

def order_block(df):
    # Practical last-opposite-candle approximation before displacement.
    if len(df) < 5:
        return {"bullish":False,"bearish":False,"price":np.nan}
    x = candle_features(df)
    a = x.iloc[-2]
    b = x.iloc[-1]
    bullish = bool(a["red"] and b["green"] and b["body"] > x["body"].tail(10).mean()*1.4)
    bearish = bool(a["green"] and b["red"] and b["body"] > x["body"].tail(10).mean()*1.4)
    return {
        "bullish":bullish,
        "bearish":bearish,
        "price":float(a["open"]) if (bullish or bearish) else np.nan
    }

def liquidity_sweep(df, lookback=10):
    if len(df) < lookback+2:
        return {"bullish":False,"bearish":False}
    prev = df.iloc[-lookback-1:-1]
    c = df.iloc[-1]
    low_sweep = c["low"] < prev["low"].min() and c["close"] > prev["low"].min()
    high_sweep = c["high"] > prev["high"].max() and c["close"] < prev["high"].max()
    return {"bullish":bool(low_sweep),"bearish":bool(high_sweep)}

# ------------------------------------------------------------
# Full indicator frame
# ------------------------------------------------------------

def build_indicators(df):
    x = candle_features(df)
    close = x["close"]

    for n in [9,21,50,100,200]:
        x[f"ema{n}"] = ema(close,n)
    for n in [20,50,200]:
        x[f"sma{n}"] = sma(close,n)

    x["rsi"] = rsi(close,14)
    x["rsi_fast"] = rsi(close,7)
    x["stoch_k"], x["stoch_d"] = stochastic(x,14,3)
    x["stochrsi_k"], x["stochrsi_d"] = stochastic_rsi(close)
    x["macd"], x["macd_signal"], x["macd_hist"] = macd(close)
    x["momentum"] = close.diff(10)
    x["cci"] = cci(x,20)
    x["bb_mid"], x["bb_upper"], x["bb_lower"] = bollinger(close,20,2)
    x["atr"] = atr(x,14)
    x["kc_mid"], x["kc_upper"], x["kc_lower"] = keltner(x)
    x["donchian_high"], x["donchian_low"] = donchian(x,20)
    x["obv"] = obv(x)
    x["vwap"] = vwap(x)
    x["mfi"] = mfi(x,14)
    x["adx"], x["plus_di"], x["minus_di"] = adx_dmi(x,14)
    x["willr"] = williams_r(x,14)
    x["ao"] = awesome_oscillator(x)
    x["uo"] = ultimate_oscillator(x)
    x["ich_tenkan"], x["ich_kijun"], x["ich_span_a"], x["ich_span_b"] = ichimoku(x)

    return x

# ------------------------------------------------------------
# Signal engine
# ------------------------------------------------------------

def add_score(scores, key, value):
    scores[key] = float(clamp(value))

def signal_engine(df, selected_strategy, enabled):
    x = build_indicators(df)
    c = x.iloc[-1]
    p = x.iloc[-2] if len(x) >= 2 else c

    bull = 0.0
    bear = 0.0
    scores = {}
    reasons = []
    warnings = []

    def B(points, reason):
        nonlocal bull
        bull += points
        reasons.append("🟢 " + reason)

    def S(points, reason):
        nonlocal bear
        bear += points
        reasons.append("🔴 " + reason)

    # EMA / trend
    ema9,ema21,ema50,ema100,ema200 = [c.get(f"ema{i}",np.nan) for i in [9,21,50,100,200]]
    if np.isfinite(ema9) and np.isfinite(ema21):
        if ema9 > ema21: B(7,"EMA 9 > EMA 21")
        if ema9 < ema21: S(7,"EMA 9 < EMA 21")
        if p.get("ema9",np.nan) <= p.get("ema21",np.nan) < ema9: B(9,"EMA 9/21 bullish crossover")
        if p.get("ema9",np.nan) >= p.get("ema21",np.nan) > ema9: S(9,"EMA 9/21 bearish crossover")
    if np.isfinite(ema50):
        if c["close"] > ema50: B(5,"Price above EMA 50")
        else: S(5,"Price below EMA 50")
    if np.isfinite(ema200):
        if c["close"] > ema200: B(4,"Price above EMA 200")
        else: S(4,"Price below EMA 200")

    # RSI
    rv = c["rsi"]
    if rv < 30: B(10,"RSI oversold")
    elif rv > 70: S(10,"RSI overbought")
    elif rv > 50: B(5,"RSI bullish zone")
    else: S(5,"RSI bearish zone")

    # MACD
    if c["macd_hist"] > 0: B(7,"MACD histogram positive")
    elif c["macd_hist"] < 0: S(7,"MACD histogram negative")
    if p["macd"] <= p["macd_signal"] < c["macd"]: B(8,"MACD bullish crossover")
    if p["macd"] >= p["macd_signal"] > c["macd"]: S(8,"MACD bearish crossover")

    # Stochastic
    if c["stoch_k"] < 20 and c["stoch_k"] > c["stoch_d"]: B(6,"Stochastic oversold recovery")
    if c["stoch_k"] > 80 and c["stoch_k"] < c["stoch_d"]: S(6,"Stochastic overbought rejection")

    # CCI
    if c["cci"] < -100: B(6,"CCI oversold")
    if c["cci"] > 100: S(6,"CCI overbought")

    # Bollinger
    if c["close"] <= c["bb_lower"]: B(8,"Bollinger lower-band reversal area")
    if c["close"] >= c["bb_upper"]: S(8,"Bollinger upper-band reversal area")

    # ADX / DMI
    if c["adx"] >= 20:
        if c["plus_di"] > c["minus_di"]: B(7,"ADX trend +DI dominant")
        elif c["minus_di"] > c["plus_di"]: S(7,"ADX trend -DI dominant")
    else:
        warnings.append("Low/sideways ADX")

    # VWAP
    if np.isfinite(c["vwap"]):
        if c["close"] > c["vwap"]: B(4,"Price above VWAP")
        else: S(4,"Price below VWAP")

    # MFI / OBV
    if c["mfi"] < 20: B(5,"MFI oversold")
    if c["mfi"] > 80: S(5,"MFI overbought")
    obv_slope = x["obv"].tail(5).diff().mean()
    if obv_slope > 0: B(3,"OBV rising")
    if obv_slope < 0: S(3,"OBV falling")

    # Williams
    if c["willr"] < -80: B(4,"Williams %R oversold")
    if c["willr"] > -20: S(4,"Williams %R overbought")

    # AO / UO
    if c["ao"] > 0: B(3,"Awesome Oscillator positive")
    else: S(3,"Awesome Oscillator negative")
    if c["uo"] > 50: B(3,"Ultimate Oscillator bullish")
    else: S(3,"Ultimate Oscillator bearish")

    # Ichimoku
    cloud_hi = max(c["ich_span_a"], c["ich_span_b"]) if np.isfinite(c["ich_span_a"]) and np.isfinite(c["ich_span_b"]) else np.nan
    cloud_lo = min(c["ich_span_a"], c["ich_span_b"]) if np.isfinite(c["ich_span_a"]) and np.isfinite(c["ich_span_b"]) else np.nan
    if np.isfinite(cloud_hi):
        if c["close"] > cloud_hi: B(5,"Price above Ichimoku cloud")
        elif c["close"] < cloud_lo: S(5,"Price below Ichimoku cloud")
        if c["ich_tenkan"] > c["ich_kijun"]: B(4,"Ichimoku Tenkan > Kijun")
        else: S(4,"Ichimoku Tenkan < Kijun")

    # Price action
    if c["pin_bull"]: B(7,"Bullish pin/rejection candle")
    if c["pin_bear"]: S(7,"Bearish pin/rejection candle")
    if c["bull_engulf"]: B(9,"Bullish engulfing")
    if c["bear_engulf"]: S(9,"Bearish engulfing")
    if c["doji"]: warnings.append("Current candle is doji-like")

    # Structure / SMC
    sr = support_resistance(x)
    structure = market_structure(x)
    fvg = fair_value_gap(x)
    ob = order_block(x)
    sweep = liquidity_sweep(x)

    if structure["bos"] == "BULLISH": B(8,"Bullish Break of Structure")
    if structure["bos"] == "BEARISH": S(8,"Bearish Break of Structure")
    if structure["choch"] == "BULLISH": B(7,"Bullish CHOCH")
    if structure["choch"] == "BEARISH": S(7,"Bearish CHOCH")
    if fvg["bullish"]: B(6,"Bullish Fair Value Gap")
    if fvg["bearish"]: S(6,"Bearish Fair Value Gap")
    if ob["bullish"]: B(6,"Bullish Order Block")
    if ob["bearish"]: S(6,"Bearish Order Block")
    if sweep["bullish"]: B(7,"Liquidity sweep below support")
    if sweep["bearish"]: S(7,"Liquidity sweep above resistance")

    support,resistance = sr
    if np.isfinite(support) and c["close"] <= support * 1.001: B(5,"Near support")
    if np.isfinite(resistance) and c["close"] >= resistance * 0.999: S(5,"Near resistance")

    # Volume strength
    vol_ma = x["volume"].rolling(20).mean()
    if np.isfinite(c["volume"]) and np.isfinite(last(vol_ma)):
        if c["volume"] > last(vol_ma)*1.5:
            if c["green"]: B(4,"High volume bullish candle")
            if c["red"]: S(4,"High volume bearish candle")

    # Filters
    range_now = c["high"] - c["low"]
    atr_now = c["atr"]
    if np.isfinite(atr_now) and atr_now > 0:
        if range_now > atr_now * 2.5:
            warnings.append("Very high volatility")
        if range_now < atr_now * 0.35:
            warnings.append("Very low volatility")

    # Enabled indicator weighting
    enabled_set = set(enabled)
    category_scores = {
        "RSI Score": clamp((max(bull,0) if "RSI" in enabled_set else 0) / 0.65),
        "MACD Score": clamp((max(bull,0) if "MACD" in enabled_set else 0) / 0.65),
        "EMA Score": clamp((max(bull,0) if any(v.startswith("EMA") for v in enabled_set) else 0) / 0.65),
        "SMC Score": clamp((max(bull,0) if any(v in enabled_set for v in ["Order Block","Fair Value Gap","Liquidity Zone","Break of Structure","CHOCH"]) else 0) / 0.65),
        "ICT Score": clamp((max(bull,0) if any(v in enabled_set for v in ["Fair Value Gap","Liquidity Zone"]) else 0) / 0.65),
        "Volume Score": clamp((max(bull,0) if any(v in enabled_set for v in ["OBV","VWAP","MFI"]) else 0) / 0.65),
        "Trend Score": clamp((max(bull,0) if any(v in enabled_set for v in ["EMA 50","EMA 100","EMA 200","ADX","DMI"]) else 0) / 0.65),
        "Volatility Score": clamp((max(bull,0) if any(v in enabled_set for v in ["ATR","Bollinger Bands","Keltner Channel","Donchian Channel"]) else 0) / 0.65),
        "Price Action Score": clamp((max(bull,0) if any(v in enabled_set for v in ["Support & Resistance","Supply & Demand","Pivot Points"]) else 0) / 0.65),
        "Pattern Recognition Score": clamp((max(bull,0) if any(v in enabled_set for v in ["Order Block","Fair Value Gap","Break of Structure","CHOCH"]) else 0) / 0.65),
    }

    # Strategy-specific boosts / restrictions
    strat = selected_strategy
    if "RSI" in strat:
        if rv < 30: bull += 12
        if rv > 70: bear += 12
    elif "EMA" in strat:
        if ema9 > ema21 > ema50: bull += 15
        if ema9 < ema21 < ema50: bear += 15
    elif "ADX" in strat:
        if c["adx"] >= 25 and c["plus_di"] > c["minus_di"]: bull += 14
        if c["adx"] >= 25 and c["minus_di"] > c["plus_di"]: bear += 14
    elif "Volatility" in strat:
        if range_now > atr_now: 
            if c["green"]: bull += 10
            else: bear += 10
    elif "Breakout" in strat:
        if c["close"] > x["high"].shift(1).rolling(20).max().iloc[-1]: bull += 15
        if c["close"] < x["low"].shift(1).rolling(20).min().iloc[-1]: bear += 15
    elif "Mean Reversion" in strat or "REVERSAL" in strat or "Reversal" in strat:
        if c["close"] <= c["bb_lower"]: bull += 12
        if c["close"] >= c["bb_upper"]: bear += 12
    elif "Momentum" in strat:
        if c["macd_hist"] > 0 and c["rsi"] > 55: bull += 10
        if c["macd_hist"] < 0 and c["rsi"] < 45: bear += 10

    # Dynamic top-N / all strategies
    if "DYNAMIC" in strat or "ALL STRATEGIES" in strat:
        pass

    total = bull + bear
    if total <= 0:
        bull_prob, bear_prob = 50.0, 50.0
    else:
        # A calibrated bounded score; not a statistical guarantee.
        raw = 50 + 50*(bull-bear)/(total+1e-9)
        bull_prob = clamp(raw, 0, 100)
        bear_prob = 100 - bull_prob

    direction = "CALL" if bull_prob > bear_prob else "PUT" if bear_prob > bull_prob else "WAIT"
    confidence = max(bull_prob,bear_prob)

    if confidence >= 95: level = "Ultra Signal"
    elif confidence >= 90: level = "Premium Signal"
    elif confidence >= 80: level = "Strong Signal"
    elif confidence >= 70: level = "Medium Signal"
    else: level = "No Strong Signal"

    if confidence < 70:
        direction = "WAIT"

    scores["Final AI Score"] = confidence
    scores["Bullish Probability"] = bull_prob
    scores["Bearish Probability"] = bear_prob

    return {
        "direction":direction,
        "confidence":confidence,
        "level":level,
        "bull":bull,
        "bear":bear,
        "scores":scores,
        "reasons":reasons[-25:],
        "warnings":warnings,
        "support":support,
        "resistance":resistance,
        "structure":structure,
        "fvg":fvg,
        "order_block":ob,
        "sweep":sweep,
        "indicators":x
    }

# ------------------------------------------------------------
# Telegram
# ------------------------------------------------------------

def telegram_send(token, chat_id, text):
    if not token or not chat_id:
        return False, "Telegram token/chat ID is not configured."
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        r = requests.post(
            url,
            json={"chat_id": chat_id, "text": text, "parse_mode":"HTML"},
            timeout=10
        )
        data = r.json()
        if not r.ok or not data.get("ok"):
            return False, str(data)
        return True, "Signal sent."
    except Exception as e:
        return False, str(e)

def format_signal(pair, timeframe, result, price, payout=None):
    payout_txt = f"\n💰 Payout: {payout}%" if payout is not None else ""
    return (
        f"📊 <b>AI SIGNAL</b>\n\n"
        f"💱 Pair: <b>{pair}</b>\n"
        f"⏱ Timeframe: <b>{timeframe}</b>\n"
        f"💵 Price: <b>{fmt(price,6)}</b>\n"
        f"🎯 Signal: <b>{result['direction']}</b>\n"
        f"📈 Confidence: <b>{result['confidence']:.1f}%</b>\n"
        f"🏷 Level: <b>{result['level']}</b>"
        f"{payout_txt}\n\n"
        f"🧠 Bullish: {result['scores']['Bullish Probability']:.1f}%\n"
        f"🧠 Bearish: {result['scores']['Bearish Probability']:.1f}%\n"
        f"🏗 BOS: {result['structure']['bos']}\n"
        f"🔄 CHOCH: {result['structure']['choch']}\n\n"
        f"⚠️ Technical probability only — not a guarantee."
    )

# ------------------------------------------------------------
# Backtest
# ------------------------------------------------------------

def backtest(df, strategy, enabled, min_conf=70, horizon=1):
    if len(df) < 120:
        return pd.DataFrame()

    rows = []
    # Evaluate only every 3rd candle to reduce CPU.
    for i in range(100, len(df)-horizon, 3):
        sub = df.iloc[:i+1].copy()
        result = signal_engine(sub, strategy, enabled)
        if result["direction"] == "WAIT" or result["confidence"] < min_conf:
            continue
        entry = float(sub["close"].iloc[-1])
        future = float(df["close"].iloc[i+horizon])
        win = (
            future > entry if result["direction"] == "CALL"
            else future < entry
        )
        rows.append({
            "time":df["datetime"].iloc[i],
            "signal":result["direction"],
            "confidence":result["confidence"],
            "entry":entry,
            "future":future,
            "result":"WIN" if win else "LOSS"
        })
    return pd.DataFrame(rows)

# ------------------------------------------------------------
# Chart
# ------------------------------------------------------------

def make_chart(df, show_ema, show_bb, show_vwap, show_sr):
    rows = 2
    fig = make_subplots(
        rows=rows, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.04,
        row_heights=[0.75,0.25]
    )
    fig.add_trace(
        go.Candlestick(
            x=df["datetime"],
            open=df["open"], high=df["high"],
            low=df["low"], close=df["close"],
            name="Candle"
        ), row=1,col=1
    )
    if show_ema:
        for n in [9,21,50,200]:
            if f"ema{n}" in df:
                fig.add_trace(go.Scatter(
                    x=df["datetime"],y=df[f"ema{n}"],
                    mode="lines",name=f"EMA {n}"
                ),row=1,col=1)
    if show_bb:
        for col,name in [("bb_upper","BB Upper"),("bb_mid","BB Basis"),("bb_lower","BB Lower")]:
            fig.add_trace(go.Scatter(
                x=df["datetime"],y=df[col],mode="lines",name=name
            ),row=1,col=1)
    if show_vwap:
        fig.add_trace(go.Scatter(
            x=df["datetime"],y=df["vwap"],mode="lines",name="VWAP"
        ),row=1,col=1)
    if show_sr:
        support,resistance = support_resistance(df)
        fig.add_hline(y=support, line_dash="dot", annotation_text="Support", row=1,col=1)
        fig.add_hline(y=resistance, line_dash="dot", annotation_text="Resistance", row=1,col=1)

    fig.add_trace(go.Bar(
        x=df["datetime"], y=df["volume"], name="Volume"
    ),row=2,col=1)

    fig.update_layout(
        height=720,
        xaxis_rangeslider_visible=False,
        margin=dict(l=10,r=10,t=30,b=10),
        legend=dict(orientation="h")
    )
    return fig

# ------------------------------------------------------------
# Session state
# ------------------------------------------------------------

defaults = {
    "telegram_enabled":False,
    "last_sent_key":"",
    "signal_history":[],
    "api_url":DEFAULT_API,
    "pair":"USDBDT_otc",
    "timeframe":"1m",
    "refresh":True,
}
for k,v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ------------------------------------------------------------
# Sidebar
# ------------------------------------------------------------

st.sidebar.title("⚙️ Control Center")

api_url = st.sidebar.text_input(
    "Candle API URL",
    value=st.session_state.api_url,
    help="Example: https://novexai.org/api.php"
)
st.session_state.api_url = api_url

pair = st.sidebar.selectbox("Asset / Pair", ALL_PAIRS, index=ALL_PAIRS.index(st.session_state.pair))
st.session_state.pair = pair

timeframe = st.sidebar.selectbox("Timeframe", list(TIMEFRAMES.keys()), index=list(TIMEFRAMES.keys()).index(st.session_state.timeframe))
st.session_state.timeframe = timeframe

count = st.sidebar.slider("History candles", 100, 1440, 500, 10)
auto_refresh = st.sidebar.checkbox("🔄 Auto refresh", value=True)
refresh_seconds = st.sidebar.slider("Refresh seconds", 2, 30, 5)

st.sidebar.divider()
strategy = st.sidebar.selectbox("🧠 Strategy / Study Mode", STRATEGIES)

st.sidebar.subheader("Indicators ON/OFF")
enabled_indicators = st.sidebar.multiselect(
    "Enable indicators",
    INDICATORS,
    default=[
        "EMA 9","EMA 21","EMA 50","EMA 200",
        "RSI","MACD","Bollinger Bands","ATR","ADX","DMI",
        "OBV","VWAP","Support & Resistance","Break of Structure","CHOCH"
    ]
)

st.sidebar.subheader("Filters")
trend_filter = st.sidebar.checkbox("Trend Filter", True)
volatility_filter = st.sidebar.checkbox("Volatility Filter", True)
sideways_filter = st.sidebar.checkbox("Sideways Market Filter", True)
fake_filter = st.sidebar.checkbox("Fake Signal Filter", True)
confirmation_filter = st.sidebar.checkbox("Confirmation Filter", True)
mtf_filter = st.sidebar.checkbox("Multi-Timeframe Filter", True)
ai_conf_filter = st.sidebar.checkbox("AI Confidence Filter", True)

st.sidebar.subheader("Signal threshold")
min_conf = st.sidebar.slider("Minimum confidence", 50, 95, 70)

st.sidebar.divider()
st.sidebar.subheader("📨 Telegram Signal")
telegram_on = st.sidebar.toggle(
    "Telegram Signal ON/OFF",
    value=st.session_state.telegram_enabled
)
st.session_state.telegram_enabled = telegram_on

telegram_token = st.sidebar.text_input(
    "Telegram Bot Token",
    value=os.getenv("TELEGRAM_BOT_TOKEN",""),
    type="password"
)
telegram_chat_id = st.sidebar.text_input(
    "Telegram Group / Channel Chat ID",
    value=os.getenv("TELEGRAM_CHAT_ID","")
)

test_telegram = st.sidebar.button("📨 Send Test Telegram")

st.sidebar.divider()
st.sidebar.caption(
    "The source API uses UTC+06:00 and returns candle fields such as "
    "open/high/low/close/direction/volume/payout."
)

# ------------------------------------------------------------
# Fetch
# ------------------------------------------------------------

try:
    with st.spinner("Loading candles..."):
        raw_df, payload = fetch_candles(api_url, pair, count)
        df = resample_candles(raw_df, timeframe)
        df = build_indicators(df)

    api_ok = True
except Exception as e:
    api_ok = False
    st.error(f"API Error: {e}")
    st.stop()

# ------------------------------------------------------------
# Header
# ------------------------------------------------------------

st.title("📊 Cortex / Quotex AI Candle Analysis Dashboard")
st.caption(
    "API → Candles → Indicators → SMC/ICT/Price Action → Score Engine → "
    "CALL/PUT/WAIT → Optional Telegram"
)

# Status cards
latest = df.iloc[-1]
result = signal_engine(df, strategy, enabled_indicators)

c1,c2,c3,c4,c5,c6 = st.columns(6)
c1.metric("API", "ONLINE" if api_ok else "OFFLINE")
c2.metric("Pair", pair)
c3.metric("Price", fmt(latest["close"],6))
c4.metric("Signal", result["direction"])
c5.metric("Confidence", f"{result['confidence']:.1f}%")
c6.metric("Level", result["level"])

# ------------------------------------------------------------
# Test telegram
# ------------------------------------------------------------

if test_telegram:
    msg = (
        "✅ <b>Telegram connection test</b>\n\n"
        f"Pair: {pair}\n"
        f"Status: {result['direction']}\n"
        f"Confidence: {result['confidence']:.1f}%"
    )
    ok, detail = telegram_send(telegram_token, telegram_chat_id, msg)
    if ok:
        st.success(detail)
    else:
        st.error(detail)

# ------------------------------------------------------------
# Automatic Telegram signal
# ------------------------------------------------------------

signal_key = f"{pair}|{timeframe}|{latest['datetime']}|{result['direction']}"

if (
    telegram_on
    and result["direction"] in ["CALL","PUT"]
    and result["confidence"] >= min_conf
    and signal_key != st.session_state.last_sent_key
):
    msg = format_signal(
        pair,
        timeframe,
        result,
        latest["close"],
        latest.get("payout", None)
    )
    ok, detail = telegram_send(telegram_token, telegram_chat_id, msg)
    if ok:
        st.session_state.last_sent_key = signal_key
        st.session_state.signal_history.append({
            "time":datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S"),
            "pair":pair,
            "tf":timeframe,
            "signal":result["direction"],
            "confidence":result["confidence"],
            "level":result["level"],
            "telegram":"SENT"
        })
        st.toast("Telegram signal sent.")
    else:
        st.warning(f"Telegram signal failed: {detail}")

# ------------------------------------------------------------
# Main chart
# ------------------------------------------------------------

show_ema = st.checkbox("Show EMA", True)
show_bb = st.checkbox("Show Bollinger Bands", False)
show_vwap = st.checkbox("Show VWAP", False)
show_sr = st.checkbox("Show Support / Resistance", True)

st.plotly_chart(
    make_chart(df.tail(min(len(df),300)), show_ema, show_bb, show_vwap, show_sr),
    use_container_width=True
)

# ------------------------------------------------------------
# Signal panel
# ------------------------------------------------------------

left,right = st.columns([1,1])

with left:
    st.subheader("🎯 Current Analysis")
    if result["direction"] == "CALL":
        st.success(f"CALL — {result['confidence']:.1f}%")
    elif result["direction"] == "PUT":
        st.error(f"PUT — {result['confidence']:.1f}%")
    else:
        st.warning(f"WAIT — {result['confidence']:.1f}%")

    st.write(f"**Signal class:** {result['level']}")
    st.write(f"**Bullish probability:** {result['scores']['Bullish Probability']:.1f}%")
    st.write(f"**Bearish probability:** {result['scores']['Bearish Probability']:.1f}%")
    st.write(f"**Support:** {fmt(result['support'],6)}")
    st.write(f"**Resistance:** {fmt(result['resistance'],6)}")
    st.write(f"**BOS:** {result['structure']['bos']}")
    st.write(f"**CHOCH:** {result['structure']['choch']}")

    st.subheader("Reasons")
    for r in result["reasons"][-15:]:
        st.write(r)

    if result["warnings"]:
        st.subheader("⚠️ Filters / Warnings")
        for w in result["warnings"]:
            st.warning(w)

with right:
    st.subheader("🧮 Component Scores")
    score_df = pd.DataFrame(
        [{"Component":k,"Score":round(v,1)} for k,v in result["scores"].items()]
    )
    st.dataframe(score_df, use_container_width=True, hide_index=True)

    st.subheader("📌 Smart Money / ICT Status")
    smc = pd.DataFrame([
        ["Order Block", "Bullish" if result["order_block"]["bullish"] else "Bearish" if result["order_block"]["bearish"] else "NONE"],
        ["Fair Value Gap", "Bullish" if result["fvg"]["bullish"] else "Bearish" if result["fvg"]["bearish"] else "NONE"],
        ["Liquidity Sweep", "Bullish" if result["sweep"]["bullish"] else "Bearish" if result["sweep"]["bearish"] else "NONE"],
        ["BOS", result["structure"]["bos"]],
        ["CHOCH", result["structure"]["choch"]],
    ], columns=["Feature","Status"])
    st.dataframe(smc, use_container_width=True, hide_index=True)

# ------------------------------------------------------------
# Indicator status table
# ------------------------------------------------------------

st.subheader("📈 Indicator Status — সব Indicator")

c = df.iloc[-1]
p = df.iloc[-2]

def status_from_values(name, value, bull_cond, bear_cond, fmt_digits=2):
    if not np.isfinite(value):
        return [name, "-", "N/A"]
    if bull_cond:
        return [name, f"{value:.{fmt_digits}f}", "🟢 BULLISH"]
    if bear_cond:
        return [name, f"{value:.{fmt_digits}f}", "🔴 BEARISH"]
    return [name, f"{value:.{fmt_digits}f}", "🟡 NEUTRAL"]

indicator_rows = []

indicator_rows += [
    status_from_values("EMA 9",c["ema9"],c["close"]>c["ema9"],c["close"]<c["ema9"],6),
    status_from_values("EMA 21",c["ema21"],c["close"]>c["ema21"],c["close"]<c["ema21"],6),
    status_from_values("EMA 50",c["ema50"],c["close"]>c["ema50"],c["close"]<c["ema50"],6),
    status_from_values("EMA 100",c["ema100"],c["close"]>c["ema100"],c["close"]<c["ema100"],6),
    status_from_values("EMA 200",c["ema200"],c["close"]>c["ema200"],c["close"]<c["ema200"],6),
    status_from_values("SMA 50",c["sma50"],c["close"]>c["sma50"],c["close"]<c["sma50"],6),
    status_from_values("SMA 200",c["sma200"],c["close"]>c["sma200"],c["close"]<c["sma200"],6),
    status_from_values("RSI",c["rsi"],c["rsi"]<30,c["rsi"]>70),
    status_from_values("Stochastic K",c["stoch_k"],c["stoch_k"]<20,c["stoch_k"]>80),
    status_from_values("Stochastic RSI K",c["stochrsi_k"],c["stochrsi_k"]<20,c["stochrsi_k"]>80),
    status_from_values("MACD Histogram",c["macd_hist"],c["macd_hist"]>0,c["macd_hist"]<0,6),
    status_from_values("CCI",c["cci"],c["cci"]<-100,c["cci"]>100),
    status_from_values("ATR",c["atr"],False,False,6),
    status_from_values("Bollinger Position",c["close"],c["close"]<c["bb_lower"],c["close"]>c["bb_upper"],6),
    status_from_values("Keltner Position",c["close"],c["close"]>c["kc_upper"],c["close"]<c["kc_lower"],6),
    status_from_values("Donchian Position",c["close"],c["close"]>=c["donchian_high"],c["close"]<=c["donchian_low"],6),
    status_from_values("OBV",c["obv"],last(df["obv"].diff())>0,last(df["obv"].diff())<0,2),
    status_from_values("VWAP",c["vwap"],c["close"]>c["vwap"],c["close"]<c["vwap"],6),
    status_from_values("MFI",c["mfi"],c["mfi"]<20,c["mfi"]>80),
    status_from_values("ADX",c["adx"],c["plus_di"]>c["minus_di"],c["minus_di"]>c["plus_di"]),
    status_from_values("+DI",c["plus_di"],c["plus_di"]>c["minus_di"],c["plus_di"]<c["minus_di"]),
    status_from_values("-DI",c["minus_di"],c["minus_di"]>c["plus_di"],c["minus_di"]<c["plus_di"]),
    status_from_values("Williams %R",c["willr"],c["willr"]<-80,c["willr"]>-20),
    status_from_values("Awesome Oscillator",c["ao"],c["ao"]>0,c["ao"]<0,6),
    status_from_values("Ultimate Oscillator",c["uo"],c["uo"]>50,c["uo"]<50),
    status_from_values("Ichimoku Tenkan/Kijun",c["ich_tenkan"],c["ich_tenkan"]>c["ich_kijun"],c["ich_tenkan"]<c["ich_kijun"],6),
]

indicator_table = pd.DataFrame(indicator_rows, columns=["Indicator","Value","Status"])
indicator_table["Enabled"] = indicator_table["Indicator"].str.replace(" Histogram","",regex=False).isin(
    [i.split(" ")[0] if i.startswith("EMA") else i for i in enabled_indicators]
)
st.dataframe(indicator_table, use_container_width=True, hide_index=True)

# ------------------------------------------------------------
# Pattern status
# ------------------------------------------------------------

st.subheader("🕯️ Price Action / Pattern Status")
patterns = pd.DataFrame([
    ["Pin Bar Bull", bool(c["pin_bull"])],
    ["Pin Bar Bear", bool(c["pin_bear"])],
    ["Bullish Engulfing", bool(c["bull_engulf"])],
    ["Bearish Engulfing", bool(c["bear_engulf"])],
    ["Inside Bar", bool(c["inside_bar"])],
    ["Doji", bool(c["doji"])],
    ["BOS", result["structure"]["bos"]],
    ["CHOCH", result["structure"]["choch"]],
    ["Order Block", "BULLISH" if result["order_block"]["bullish"] else "BEARISH" if result["order_block"]["bearish"] else "NONE"],
    ["FVG", "BULLISH" if result["fvg"]["bullish"] else "BEARISH" if result["fvg"]["bearish"] else "NONE"],
    ["Liquidity Sweep", "BULLISH" if result["sweep"]["bullish"] else "BEARISH" if result["sweep"]["bearish"] else "NONE"],
],columns=["Pattern","Status"])
st.dataframe(patterns,use_container_width=True,hide_index=True)

# ------------------------------------------------------------
# Multi-timeframe snapshot
# ------------------------------------------------------------

if mtf_filter:
    st.subheader("🕐 Multi-Timeframe Confirmation")
    mtf_rows = []
    for tf in ["1m","5m","15m","30m"]:
        try:
            tx = resample_candles(raw_df,tf)
            if len(tx) < 80:
                mtf_rows.append([tf,"INSUFFICIENT","-"])
                continue
            rr = signal_engine(tx,strategy,enabled_indicators)
            mtf_rows.append([tf,rr["direction"],f"{rr['confidence']:.1f}%"])
        except Exception as e:
            mtf_rows.append([tf,"ERROR","-"])
    st.dataframe(pd.DataFrame(mtf_rows,columns=["Timeframe","Signal","Confidence"]),use_container_width=True,hide_index=True)

# ------------------------------------------------------------
# Backtest
# ------------------------------------------------------------

st.subheader("🧪 Historical Signal Test")
bt_col1,bt_col2,bt_col3 = st.columns(3)
with bt_col1:
    run_bt = st.button("▶ Run Backtest")
with bt_col2:
    bt_horizon = st.selectbox("Future candle", [1,2,3,5], index=0)
with bt_col3:
    bt_threshold = st.slider("Backtest confidence",50,95,70)

if run_bt:
    with st.spinner("Running backtest..."):
        bt = backtest(raw_df,strategy,enabled_indicators,bt_threshold,bt_horizon)
    if bt.empty:
        st.warning("No qualifying signals.")
    else:
        wins = int((bt["result"]=="WIN").sum())
        total = len(bt)
        wr = 100*wins/total if total else 0
        a,b,c2,d = st.columns(4)
        a.metric("Signals",total)
        b.metric("Wins",wins)
        c2.metric("Losses",total-wins)
        d.metric("Observed Win Rate",f"{wr:.1f}%")
        st.dataframe(bt.tail(100),use_container_width=True,hide_index=True)

# ------------------------------------------------------------
# Telegram history
# ------------------------------------------------------------

st.subheader("📨 Telegram Signal History")
if st.session_state.signal_history:
    st.dataframe(
        pd.DataFrame(st.session_state.signal_history).tail(100),
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("No Telegram signals sent in this session.")

# ------------------------------------------------------------
# Raw API status
# ------------------------------------------------------------

with st.expander("🔌 API Status / Raw Response"):
    st.json({
        "success": payload.get("success"),
        "pair": payload.get("pair"),
        "count": payload.get("count"),
        "timezone": payload.get("Time zone"),
        "timeframe": payload.get("TimeFrame"),
        "execution_time": payload.get("Execution_time"),
        "rows_loaded": len(raw_df),
        "last_candle": str(raw_df["datetime"].iloc[-1]),
    })

# ------------------------------------------------------------
# Auto refresh
# ------------------------------------------------------------

if auto_refresh:
    time.sleep(refresh_seconds)
    st.rerun()
