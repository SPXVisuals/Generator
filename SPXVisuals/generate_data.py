import os
import json
import pandas as pd
import yfinance as yf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
import seaborn as sns
from logger import log
import random
import sys
import warnings
import math

warnings.filterwarnings("ignore", message=".*not compatible with tight_layout.*")
plt.rcParams["figure.autolayout"] = True
sns.set_style("whitegrid")

# ---------------- CONFIG ----------------
HISTORY_PERIOD = "10y"
SMA_EMA_TIMEFRAME = "1y"

SMA_PERIODS = [20, 50, 100, 200]
EMA_PERIODS = [9, 20, 50, 200]

SPX_TICKER = "^GSPC"

OUTPUT_DIRS = [
    "output/normalized",
    "output/ma",
    "output/marketcap",
    "output/pe",
    "output/volume",
    "output/metadata",
    "output/leaders_laggards"
]

for d in OUTPUT_DIRS:
    os.makedirs(d, exist_ok=True)

SCHEDULE = {
    "Monday": {"timeframe": "3y"},
    "Tuesday": {"timeframe": "1y"},
    "Wednesday": {"timeframe": "3mo"},
    "Thursday": {"timeframe": "1mo"},
    "Friday": {"timeframe": "1w"},
    "Saturday": {"timeframe": "YTD"},
    "Sunday": {"fundamentals": True},
}


# ---------------- HELPERS ----------------
def format_market_cap(mc):
    if mc >= 1e12:
        return f"{mc / 1e12:.2f}T"
    return f"{mc / 1e9:.2f}B"


def get_days_to_plot(timeframe, close_series=None):
    mapping = {
        "1w": 5,
        "1mo": 21,
        "3mo": 63,
        "1y": 252,
        "3y": 756
    }

    if close_series is None:
        return pd.Series(dtype=float)

    if timeframe == "YTD":
        # Include Dec 31 of previous year if available
        prev_year_end = pd.Timestamp(f"{datetime.now().year - 1}-12-31", tz=close_series.index.tz)
        year_start = pd.Timestamp(f"{datetime.now().year}-01-01", tz=close_series.index.tz)
        # Take Dec 31 row if exists
        start_idx = close_series.index.get_loc(prev_year_end) if prev_year_end in close_series.index else \
        close_series.index.get_indexer([year_start])[0]
        return close_series.iloc[start_idx:]
    else:
        days = mapping.get(timeframe, 252)
        return close_series.iloc[-days:]


# ---------------- LOAD HOLDINGS ----------------
def load_holdings(csv_path):
    log(f"Loading holdings from sandpcomponents.csv")
    df = pd.read_csv(csv_path)
    df["Symbol"] = df["Symbol"].astype(str).str.strip()
    sp500 = {}
    for _, row in df.iterrows():
        ticker = row["Symbol"]
        if not ticker:
            continue
        sp500[ticker] = {
            "Name": row["Security"],
            "Sector": row.get("GICS Sector", "Unknown"),
            "SubIndustry": row.get("GICS Sub-Industry", "Unknown"),
        }
    log(f"Loaded {len(sp500)} tickers")
    return sp500


# ---------------- FETCH MARKET DATA ----------------
def fetch_market_data(sp500):
    for t in sp500:
        try:
            tk = yf.Ticker(t)
            log(f"Fetching data for {t}")

            info = tk.info or {}
            fi = getattr(tk, "fast_info", {}) or {}

            # --- Price fallback ---
            price = (
                info.get("regularMarketPrice")
                or fi.get("last_price")
                or fi.get("lastPrice")
            )

            # --- Shares fallback ---
            shares = (
                info.get("sharesOutstanding")
                or fi.get("shares_outstanding")
                or fi.get("sharesOutstanding")
            )

            if not price or not shares:
                log(f"[WARN] Missing price/shares for {t}")
                sp500[t]["price"] = price
                sp500[t]["market_cap"] = None
            else:
                sp500[t]["price"] = float(price)
                sp500[t]["market_cap"] = float(price) * float(shares)

            # --- Valuation ---
            sp500[t]["trailingPE"] = info.get("trailingPE")
            sp500[t]["forwardPE"] = info.get("forwardPE")

            # --- History safe fetch ---
            hist = tk.history(period=HISTORY_PERIOD)

            if hist is None or hist.empty:
                log(f"[WARN] Empty history for {t}")
                continue

            # Store Close and Volume
            sp500[t]["close"] = hist["Close"]
            sp500[t]["Volume"] = hist["Volume"]  # <-- NEW

            for p in SMA_PERIODS:
                sp500[t][f"SMA{p}"] = hist["Close"].rolling(p).mean()

            for p in EMA_PERIODS:
                sp500[t][f"EMA{p}"] = hist["Close"].ewm(span=p, adjust=False).mean()

            log(f"Successfully fetched data for {t}")

        except Exception as e:
            log(f"Failed fetching {t}: {e}")
            continue


# ---------------- RANKING ----------------
def rank_by_market_cap(sp500):
    def valid_market_cap(t):
        mc = sp500[t].get("market_cap")
        return isinstance(mc, (int, float)) and not math.isnan(mc)

    ranked = sorted(
        [t for t in sp500 if valid_market_cap(t)],
        key=lambda x: sp500[x]["market_cap"],
        reverse=True
    )

    ranks = {t: i + 1 for i, t in enumerate(ranked)}
    return ranked, ranks


# SPX period performance
def compute_spx_performance(timeframe):
    spx_close = yf.Ticker(SPX_TICKER).history(period=HISTORY_PERIOD)["Close"]
    spx_period = get_days_to_plot(timeframe, spx_close)
    if len(spx_period) < 2:
        return None
    spx_then = spx_period.iloc[0]
    spx_now = spx_period.iloc[-1]
    spx_change = spx_now - spx_then
    spx_pct = (spx_now / spx_then - 1) * 100
    return {
        "spx_then": spx_then,
        "spx_now": spx_now,
        "spx_change": spx_change,
        "spx_pct": spx_pct
    }


# ---------------- DAILY PERFORMANCE (UPDATED FOR INTRADAY) ----------------
def compute_daily_performance(sp500):
    rows = []

    # Fetch SPX intraday price
    spx_ticker = yf.Ticker(SPX_TICKER)
    spx_hist = spx_ticker.history(period="5d")  # ensure prior trading day exists
    if len(spx_hist) < 2:
        log("[WARN] Not enough SPX history for daily performance")
        return pd.DataFrame(), {}

    # Yesterday close
    spx_close_yesterday = spx_hist["Close"].iloc[-2]

    # Today intraday price
    spx_today_price = spx_ticker.fast_info.last_price or spx_hist["Close"].iloc[-1]

    spx_change = spx_today_price - spx_close_yesterday
    spx_pct = (spx_today_price / spx_close_yesterday - 1) * 100
    spx_perf = {
        "spx_then": spx_close_yesterday,
        "spx_now": spx_today_price,
        "spx_change": spx_change,
        "spx_pct": spx_pct
    }

    for t, d in sp500.items():
        close_series = d.get("close")
        if close_series is None or len(close_series) < 2:
            continue

        # Yesterday close
        price_yesterday = close_series.iloc[-2]

        # Today intraday price (fallback to last close if market closed)
        price_today = d.get("price") or close_series.iloc[-1]

        change = price_today - price_yesterday
        pct_change = (price_today / price_yesterday - 1) * 100

        rows.append({
            "Ticker": t,
            "Beginning Price": price_yesterday,
            "Current Price": price_today,
            "Change In Price": change,
            "Percent Change": pct_change,
            "SPX Change": spx_change,
            "SPX Percent Change": spx_pct
        })

    df = pd.DataFrame(rows)
    return df, spx_perf

# Period Performance
def compute_period_performance(sp500, timeframe):
    rows = []
    spx_perf = compute_spx_performance(timeframe)

    for t, d in sp500.items():
        close = d.get("close")
        price_now = d.get("price")
        if close is None or price_now is None or close.empty:
            continue

        period_close = get_days_to_plot(timeframe, close)

        # Skip if still less than 2 points
        if len(period_close) < 2:
            # Fallback: Use Dec 31 close for YTD if available
            if timeframe == "YTD":
                prev_year_end = pd.Timestamp(f"{datetime.now().year - 1}-12-31", tz=close.index.tz)
                if prev_year_end in close.index:
                    period_close = close.loc[[prev_year_end, close.index[-1]]]
                else:
                    continue
            else:
                continue

        price_then = period_close.iloc[0]
        price_now_hist = period_close.iloc[-1]
        change = price_now_hist - price_then
        pct_change = (price_now_hist / price_then - 1) * 100

        rows.append({
            "Ticker": t,
            "Beginning Price": price_then,
            "Current Price": price_now,
            "Change In Price": change,
            "Percent Change": pct_change,
            "SPX Change": spx_perf["spx_change"],
            "SPX Percent Change": spx_perf["spx_pct"]
        })

    df = pd.DataFrame(rows)
    return df


# ---------------- NORMALIZED PRICE CHARTS ----------------
def plot_normalized_prices(sp500, ranks, tickers, timeframe, date_str=None):  # UPDATED
    outputs = []
    spx = yf.Ticker(SPX_TICKER).history(period=HISTORY_PERIOD)["Close"]
    spx_close = get_days_to_plot(timeframe, spx)
    spx_norm = spx_close / spx_close.iloc[0] * 100
    spx_pct = (spx_close.iloc[-1] / spx_close.iloc[0] - 1) * 100

    for i in range(0, len(tickers), 10):
        group = tickers[i:i + 10]
        plt.figure(figsize=(14, 7), dpi=200)
        plt.plot(spx_norm, label=f"SPX ({spx_pct:+.2f}%)", linewidth=3, color="black")
        perf = []
        for t in group:
            c = get_days_to_plot(timeframe, sp500[t]["close"])
            norm = c / c.iloc[0] * 100
            pct = (c.iloc[-1] / c.iloc[0] - 1) * 100
            perf.append((t, norm, pct))
        perf.sort(key=lambda x: x[2], reverse=True)
        for t, norm, pct in perf:
            plt.plot(norm, label=f"{t} ({pct:+.2f}%) (#{ranks[t]} Market Cap)")
        plt.title(
            f"{timeframe} - Normalized Prices - #{ranks[group[0]]} - #{ranks[group[-1]]} Largest By Market Capitalization",
            fontsize=14
        )
        plt.legend(fontsize=9)
        path = f"output/normalized/{date_str}_{timeframe}_{i // 10}.png"  # UPDATED
        plt.savefig(path)
        plt.close()
        outputs.append(path)
    return outputs


# ---------------- DONUT CHART ----------------
def donut_chart_with_rest(sp500, tickers, title, sp500_total_mc, path):
    values = [sp500[t]["market_cap"] for t in tickers]
    rest_value = sp500_total_mc - sum(values)
    fig, ax = plt.subplots(figsize=(10, 10), dpi=200)
    wedges, _ = ax.pie(
        values,
        radius=1.0,
        startangle=140,
        wedgeprops=dict(width=0.3, edgecolor="white")
    )
    ax.pie(
        [rest_value],
        radius=0.7,
        colors=["lightgray"],
        startangle=140,
        wedgeprops=dict(width=0.3, edgecolor="white")
    )
    for wedge, t in zip(wedges, tickers):
        ang = (wedge.theta2 + wedge.theta1) / 2
        x, y = np.cos(np.deg2rad(ang)), np.sin(np.deg2rad(ang))
        pct = sp500[t]["market_cap"] / sp500_total_mc * 100
        ax.annotate(
            f"{t} {pct:.2f}%",
            xy=(x * 0.85, y * 0.85),
            xytext=(x * 1.25, y * 1.25),
            arrowprops=dict(arrowstyle="-", color="black"),
            ha="center",
            va="center",
            fontsize=9
        )
    rest_pct = rest_value / sp500_total_mc * 100
    ax.text(
        0, 0,
        f"Rest of Index\n{rest_pct:.2f}%",
        ha="center",
        va="center",
        fontsize=12,
        weight="bold"
    )
    ax.set_title(title, fontsize=14)
    plt.savefig(path)
    log(f"Created marketcap chart: {path}")
    plt.close()


# ---------------- P/E BAR CHARTS ----------------
def plot_pe_bar_charts_fixed(sp500, tickers, date_str=None):  # UPDATED
    paths = []

    def plot_metric(key, title, ylabel, fname):
        rows = []
        spy_pe = yf.Ticker("SPY").info.get(key)
        if spy_pe and spy_pe > 0:
            rows.append({"Ticker": "SPY", "Value": spy_pe, "Color": "SPY"})
        for t in tickers:
            pe = sp500[t].get(key)
            if pe and pe > 0:
                rows.append({"Ticker": t, "Value": pe, "Color": "Other"})
        df = pd.DataFrame(rows).sort_values("Value", ascending=False)
        plt.figure(figsize=(18, 7), dpi=200)

        ax = sns.barplot(
        data=df,
        x="Ticker",
        y="Value",
        hue="Color",
        palette={"SPY": "black", "Other": "skyblue"},
        dodge=False,
        legend=False
        )

        y_max = df["Value"].max()
        ax.set_ylim(0, y_max * 1.05)

        for i, v in enumerate(df["Value"]):
            ax.text(
                i,
                v + y_max * 0.005,
                f"{v:.2f}",
                ha="center",
                va="bottom",
                fontsize=9,
                rotation=90
            )

        plt.ylabel(ylabel)
        plt.title(title, fontsize=14)
        plt.xticks(rotation=90)
        plt.tight_layout()
        path = f"output/pe/{date_str}_{fname}.png"  # UPDATED
        plt.savefig(path)
        plt.close()
        paths.append(path)

    plot_metric("trailingPE", "Trailing P/E – #1 - #50 Largest By Market Capitalization", "P/E", "pe_trailing")
    plot_metric("forwardPE", "Forward P/E – #1 - #50 Largest By Market Capitalization", "Forward P/E", "pe_forward")
    log(f"Created P/E chart: {paths}")
    return paths


# ---------------- VOLUME BAR CHARTS ----------------
def plot_top_volume_bar(sp500, top_n, timeframe, date_str):
    volumes = {}
    for t, d in sp500.items():
        vol_series = d.get("Volume")
        if vol_series is None or vol_series.empty:
            continue
        period_vol = get_days_to_plot(timeframe, vol_series).sum()
        volumes[t] = period_vol

    if not volumes:
        log(f"No volume data available for timeframe {timeframe}")
        return []

    top_volumes = dict(sorted(volumes.items(), key=lambda x: x[1], reverse=True)[:top_n])

    # Convert to DataFrame and scale volume to millions
    df = pd.DataFrame({
        "Ticker": list(top_volumes.keys()),
        "Volume": [v / 1e6 for v in top_volumes.values()]  # scale to millions
    }).sort_values("Volume", ascending=False)

    # Add Percent column
    total_vol = df["Volume"].sum()
    df["Percent"] = df["Volume"] / total_vol * 100

    plt.figure(figsize=(18, 7), dpi=200)
    ax = sns.barplot(
        data=df,
        x="Ticker",
        y="Volume",
        color="skyblue",
        dodge=False
    )
    
    y_max = df["Volume"].max()
    ax.set_ylim(0, y_max * 1.06)


    for i, row in enumerate(df.itertuples()):
        ax.text(
        i,
        row.Volume + y_max * 0.01,
        f"{row.Volume:.1f}M ({row.Percent:.2f}%)",
        ha="center",
        va="bottom",
        fontsize=9,
        rotation=90
        )


    plt.ylabel("Volume (Millions)")
    plt.xlabel("Ticker")
    plt.title(f"{timeframe} - Volume Distribution - #1 - #50 Largest By Volume", fontsize=14)
    plt.xticks(rotation=90)
    plt.tight_layout()

    path = f"output/volume/{date_str}_top_volume_{timeframe}.png"
    plt.savefig(path)
    plt.close()
    log(f"Created top volume bar chart (y-axis in millions): {path}")
    return [path]

# ---------------- SMA / EMA CHARTS ----------------
def plot_ma_simple(sp500, ranks, ticker, ma_type, timeframe, date_str=None):  # UPDATED
    d = sp500[ticker]
    close = get_days_to_plot(timeframe, d["close"])
    plt.figure(figsize=(14, 7), dpi=200)
    plt.plot(
        close,
        label=f"{ticker} (${d['price']:.2f}) ({format_market_cap(d['market_cap'])}) (#{ranks[ticker]} Market Cap)",
        color="black"
    )
    periods = SMA_PERIODS if ma_type == "SMA" else EMA_PERIODS
    for p in periods:
        series = get_days_to_plot(timeframe, d[f"{ma_type}{p}"])
        plt.plot(series, label=f"{ma_type}{p} (${series.iloc[-1]:.2f})")
    plt.title(f"{timeframe} - {ticker} {ma_type} – #{ranks[ticker]} Largest By Market Capitalization", fontsize=14)
    plt.legend(fontsize=9)
    path = f"output/ma/{date_str}_{ticker}_{ma_type}_{timeframe}.png"  # UPDATED
    plt.savefig(path)
    plt.close()
    log(f"Created SMA & EMA charts for {ticker}")
    return path


def plot_gainers_losers(df, timeframe, spx_perf, save_path=None):
    df = df.sort_values("Percent Change", ascending=False)
    gainers = df.head(25)
    losers = df.tail(25).sort_values("Percent Change")

    fig = plt.figure(figsize=(22, 11), dpi=200)
    gs = fig.add_gridspec(
        nrows=2,
        ncols=2,
        height_ratios=[0.05, 0.95],
        hspace=0.01,
        wspace=0.04
    )
    fig.subplots_adjust(left=0.02, right=0.98, top=0.93, bottom=0.04)

    ax_spx = fig.add_subplot(gs[0, :])
    ax_spx.set_axis_off()
    spx_then = spx_perf["spx_then"]
    spx_now = spx_perf["spx_now"]
    spx_change = spx_now - spx_then
    spx_pct = spx_change / spx_then * 100

    ax_spx.text(
        0.5,
        0.5,
        f"SPX Performance Over The Period: {spx_change:+.2f} Points {spx_pct:+.2f}%",
        ha="center",
        va="center",
        fontsize=15,
        weight="bold",
        color="black"
    )

    ax_g = fig.add_subplot(gs[1, 0])
    ax_l = fig.add_subplot(gs[1, 1])

    def draw_table(ax, data, title, title_color):
        ax.set_axis_off()
        table_data = []
        for _, r in data.iterrows():
            table_data.append([
                r["Ticker"],
                f"${r[f'Beginning Price']:.2f}",
                f"${r['Current Price']:.2f}",
                f"{r['Change In Price']:+.2f}",
                f"{r['Percent Change']:+.2f}%"
            ])
        col_labels = [
            "Ticker",
            "Beginning Price",
            "Current Price",
            "Change In Price ($)",
            "Percent Change"
        ]
        table = ax.table(
            cellText=table_data,
            colLabels=col_labels,
            cellLoc="center",
            loc="upper center",
            colWidths=[0.12, 0.18, 0.18, 0.22, 0.18]
        )
        table.auto_set_font_size(False)
        table.set_fontsize(13)
        table.scale(1.0, 1.9)

        for col in range(len(col_labels)):
            header = table[(0, col)]
            header.set_text_props(weight="bold")
            header.set_facecolor("#e6e6e6")

        for row in range(1, len(table_data) + 1):
            change_value = float(data.iloc[row - 1]["Change In Price"])
            pct_value = float(data.iloc[row - 1]["Percent Change"])
            table[(row, 3)].get_text().set_color("#2E7D32" if change_value > 0 else "#C62828")
            table[(row, 4)].get_text().set_color("#2E7D32" if pct_value > 0 else "#C62828")

        ax.set_title(title, fontsize=15, weight="bold", color=title_color, pad=6)

    draw_table(ax_g, gainers, "LEADERS", "black")
    draw_table(ax_l, losers, "LAGGARDS", "black")

    plt.suptitle(f"{timeframe} - S&P 500 Performance Leaders & Laggards", fontsize=17, weight="bold", y=0.97)

    path = save_path or f"output/leaders_laggards/gainers_losers_{timeframe}.png"
    plt.savefig(path, pad_inches=0.15)
    plt.close()
    log(f"Created gainers/losers chart: {path}")
    return path


# ---------------- RUN TODAY ----------------
def run_today(mode):
    day = datetime.now().strftime("%A")
    date_str = datetime.now().strftime("%Y-%m-%d")  # NEW
    log(f"Starting run_today() for {day}")
    cfg = SCHEDULE.get(day)
    if not cfg:
        return

    sp500 = load_holdings("sandpcomponents.csv")
    fetch_market_data(sp500)
    ranked, ranks = rank_by_market_cap(sp500)
    top50 = ranked[:50]
    top40 = ranked[:40]
    posts = []

    if mode == "AM":
        # ---------------- DAILY LEADERS/LAGGARDS ----------------
        if day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]:
            daily_df, spx_perf = compute_daily_performance(sp500)
            daily_path = f"output/leaders_laggards/{date_str}_daily_gainers_losers.png"
            plot_gainers_losers(daily_df, "Daily", spx_perf, save_path=daily_path)
            posts.append({
                "type": "gainers_losers",
                "images": [daily_path],
                "timeframe": "Daily",
            })

        if cfg.get("fundamentals"):
            total_mc = sum(v.get("market_cap") or 0 for v in sp500.values())
            ranges = [
                (top50[:10], "1_10"),
                (top50[10:25], "11_25"),
                (top50[25:50], "26_50"),
            ]
            # MarketCap charts
            marketcap_images = []
            for tickers, label in ranges:
                path = f"output/marketcap/{date_str}_marketcap_{label}.png"
                donut_chart_with_rest(
                    sp500,
                    tickers,
                    f"Market Capitalization Distribution – #{label.replace('_', ' – #')} Largest By Market Capitalization",
                    total_mc,
                    path
                )
                marketcap_images.append(path)
            posts.append({
                "type": "marketcap",
                "images": marketcap_images,
                "label": "1_50"
            })

            # P/E charts
            pe_paths = plot_pe_bar_charts_fixed(sp500, top50, date_str=date_str)
            if pe_paths:
                posts.append({
                "type": "pe",
                "images": pe_paths
                })

            # ---------------- TOP VOLUME CHARTS ----------------
            volume_timeframes = ["1w", "1mo", "YTD", "1y"]
            volume_images = []

            for tf in volume_timeframes:
                img_paths = plot_top_volume_bar(sp500, top_n=50, timeframe=tf, date_str=date_str)
                volume_images.extend(img_paths)

            posts.append({
                "type": "volume",
                "images": volume_images
            })
    else:
        timeframe = cfg.get("timeframe")
        if not timeframe:
            log(f"No timeframe defined for {day}, skipping PM charts.")
            return

        # Gainers And Losers
        perf_df = compute_period_performance(sp500, timeframe)
        spx_perf = compute_spx_performance(timeframe)

        # If YTD and only one row, use Dec 31 previous year as starting point
        if timeframe == "YTD" and perf_df.shape[0] == 1:
            t = perf_df.iloc[0]["Ticker"]
            close_series = sp500[t]["close"]
            dec31 = pd.Timestamp(f"{datetime.now().year-1}-12-31", tz=close_series.index.tz)
            if dec31 in close_series.index:
                price_then = close_series.loc[dec31]
                price_now = perf_df.iloc[0]["Current Price"]
                change = price_now - price_then
                pct_change = (price_now / price_then - 1) * 100
                perf_df.at[0, "Beginning Price"] = price_then
                perf_df.at[0, "Change In Price"] = change
                perf_df.at[0, "Percent Change"] = pct_change

        gl_path = f"output/leaders_laggards/{date_str}_gainers_losers_{timeframe}.png"  # UPDATED
        plot_gainers_losers(perf_df, timeframe, spx_perf, save_path=gl_path)  # UPDATED
        posts.append({
            "type": "gainers_losers",
            "images": [gl_path],
            "timeframe": timeframe
        })

        # Normalized price charts
        norm_paths = plot_normalized_prices(sp500, ranks, top40, timeframe, date_str=date_str)  # UPDATED
        posts.append({
            "type": "normalized",
            "images": norm_paths,
            "label": "1_40"
        })

        # SMA / EMA charts
        for t in random.sample(ranked, k=3):
            posts.append({
                "type": "ma",
                "ticker": t,
                "images": [
                    plot_ma_simple(sp500, ranks, t, "SMA", SMA_EMA_TIMEFRAME, date_str=date_str),  # UPDATED
                    plot_ma_simple(sp500, ranks, t, "EMA", SMA_EMA_TIMEFRAME, date_str=date_str),  # UPDATED
                ]
            })

    # Save metadata JSON
    meta_path = f"output/metadata/posts_{date_str}_{mode.lower()}.json"  # UPDATED
    with open(meta_path, "w") as f:
        json.dump(posts, f, indent=2)
    log(f"Saved metadata JSON: {meta_path}")
    log("run_today() completed")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "PM"
    run_today(mode=mode)








