"""
GPT Prompt: Create a stock trading strategy using Bollinger Bands with compound returns tracking
Features:
- Backtest strategy for 2014–2025
- Uses Bollinger Bands for buy/sell signals
- Sequential trades allowed (same-day rebuys)
- Creates trade spreadsheet + metrics
- Generates charts
- Calculates compound returns per year and over 12 years
"""

import pandas as pd, numpy as np, os, glob, mplfinance as mpf, matplotlib.pyplot as plt
from datetime import datetime

# --- Strategy Parameters ---
period, std_factor = 20, 2
max_hold_days, min_volume = 30, 100000
deviation_threshold = 0.02
initial_capital = 10000
years_to_test = list(range(2014, 2026))

strategy_description = (
    "We use daily Adj Close prices to generate buy signals when the price falls below the "
    "lower Bollinger Band (20-day, 2σ), provided the deviation is >2% and volume >100k. "
    "Sell when the price crosses the SMA or after 30 days. Capital compounds after each trade."
)

def calculate_bands(df):
    df["SMA"] = df["Close"].rolling(period).mean()
    df["STD"] = df["Close"].rolling(period).std()
    df["Upper"] = df["SMA"] + std_factor * df["STD"]
    df["Lower"] = df["SMA"] - std_factor * df["STD"]
    df["%Below_Lower"] = (df["Lower"] - df["Close"]) / df["Close"]
    return df

def find_signals(df):
    trades, in_position, entry_date, entry_price = [], False, None, None
    for i in range(len(df)):
        today = df.index[i]
        price, vol = df["Close"].iloc[i], df["Volume"].iloc[i]
        sma, lower, below = df["SMA"].iloc[i], df["Lower"].iloc[i], df["%Below_Lower"].iloc[i]
        if not in_position:
            if price < lower and below > deviation_threshold and vol > min_volume:
                in_position, entry_date, entry_price = True, today, price
        else:
            days_held = (today - entry_date).days
            if price > sma or days_held >= max_hold_days:
                trades.append((entry_date, entry_price, today, price, below, days_held))
                in_position = False
    return trades

def plot_chart(df, signals, ticker, year):
    os.makedirs("plots", exist_ok=True)
    apds = [mpf.make_addplot(df["Upper"], color='gray', alpha=0.5),
            mpf.make_addplot(df["Lower"], color='gray', alpha=0.5),
            mpf.make_addplot(df["SMA"], color='blue', alpha=0.5)]
    vdates, vcols = [], []
    for s in signals:
        vdates += [s[0], s[2]]
        vcols += ["g", "r"]
    fig, _ = mpf.plot(df, type='candle', volume=True, addplot=apds, style='yahoo',
                      vlines=dict(vlines=vdates, colors=vcols, linewidths=1, linestyle='--'),
                      title=f"{ticker} {year} Signals", returnfig=True)
    fig.savefig(f"plots/{ticker}_{year}.png"); plt.close(fig)

def backtest_year(year):
    all_trades, compound_returns = [], {}
    for csv in glob.glob("YahooStockData/*.csv"):
        ticker = os.path.basename(csv).replace(".csv", "")
        df = pd.read_csv(csv)
        df["Date"] = pd.to_datetime(df["Date"]); df.set_index("Date", inplace=True)
        df = df[df.index.year == year]
        if len(df) < period: continue
        df = calculate_bands(df).dropna()
        signals = find_signals(df)
        if not signals: continue

        capital = initial_capital
        for s in signals:
            shares = capital / s[1]
            capital = shares * s[3]

        compound_returns[ticker] = (capital - initial_capital) / initial_capital * 100
        for s in signals:
            pct = (s[3] - s[1]) / s[1] * 100
            all_trades.append([ticker, s[0], s[1], s[2], s[3], pct, s[4], s[5]])
        plot_chart(df, signals, ticker, year)

    if all_trades:
        pd.DataFrame(all_trades, columns=["Ticker","Buy_Date","Buy_Price","Sell_Date","Sell_Price",
                                          "Profit%","%Below_Lower","Days_Held"]).to_csv(f"{year}_perf.csv", index=False)
    avg_return = np.mean(list(compound_returns.values())) if compound_returns else 0
    return avg_return

def multi_year_backtest():
    os.makedirs("plots", exist_ok=True)
    with open("results.txt", "w", encoding='utf-8') as f:
        f.write("Strategy Description:\n" + strategy_description + "\n\n")
        f.write("GPT Prompt:\nCreate a stock trading strategy using Bollinger Bands with compound returns tracking\n\n")
        f.write("Multi-Year Backtest Results (2014–2025)\n" + "="*50 + "\n")

        comp_factor = 1
        for year in years_to_test[::-1]:  # Reverse order for reporting
            gain = backtest_year(year)
            comp_factor *= (1 + gain / 100)
            f.write(f"Finished processing year {year}. Compounded gain: {gain:.2f}%\n")
        f.write("\nFinal Compounded Return (2014–2025): {:.3f}x\n".format(comp_factor))
        print(f"\n12-Year Compound Growth: {comp_factor:.3f}x\nResults saved to results.txt")

if __name__ == "__main__":
    multi_year_backtest()
