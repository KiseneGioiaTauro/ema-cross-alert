import os
import sys
import json
import requests

API_KEY = os.environ.get("TWELVE_DATA_API_KEY")
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

SYMBOL = os.environ.get("SYMBOL") or "EUR/USD"
INTERVAL = os.environ.get("INTERVAL") or "5min"
FAST_PERIOD = int(os.environ.get("FAST_PERIOD") or "34")
SLOW_PERIOD = int(os.environ.get("SLOW_PERIOD") or "144")

STATE_DIR = "state"
STATE_FILE = os.path.join(STATE_DIR, "last_candle.json")


def compute_ema(values, period):
    k = 2 / (period + 1)
    ema = [None] * len(values)
    if len(values) < period:
        return ema
    seed = sum(values[:period]) / period
    ema[period - 1] = seed
    for i in range(period, len(values)):
        ema[i] = values[i] * k + ema[i - 1] * (1 - k)
    return ema


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def save_state(state):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def send_telegram(text):
    if not BOT_TOKEN or not CHAT_ID:
        print("Telegram non configurato (manca token o chat id), salto invio:")
        print(text)
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        resp = requests.post(url, json={"chat_id": CHAT_ID, "text": text}, timeout=15)
        if resp.status_code != 200:
            print("Errore invio Telegram:", resp.status_code, resp.text)
        else:
            print("Messaggio Telegram inviato.")
    except requests.RequestException as e:
        print("Eccezione durante invio Telegram:", e)


def main():
    if not API_KEY:
        print("Manca TWELVE_DATA_API_KEY: imposta il secret nel repository GitHub.")
        sys.exit(1)

    outputsize = max(SLOW_PERIOD * 4, 300)
    url = (
        "https://api.twelvedata.com/time_series"
        f"?symbol={SYMBOL}&interval={INTERVAL}&outputsize={outputsize}&apikey={API_KEY}"
    )

    try:
        resp = requests.get(url, timeout=20)
        data = resp.json()
    except requests.RequestException as e:
        print("Errore di rete verso Twelve Data:", e)
        sys.exit(0)

    if "values" not in data:
        print("Risposta API senza dati utili:", data)
        sys.exit(0)

    values = list(reversed(data["values"]))
    closes = [float(v["close"]) for v in values]
    times = [v["datetime"] for v in values]

    if len(closes) < SLOW_PERIOD + 2:
        print(f"Dati storici insufficienti per EMA {SLOW_PERIOD} (ricevute {len(closes)} candele).")
        sys.exit(0)

    ema_fast = compute_ema(closes, FAST_PERIOD)
    ema_slow = compute_ema(closes, SLOW_PERIOD)
    n = len(closes)

    diff_prev = ema_fast[n - 2] - ema_slow[n - 2]
    diff_last = ema_fast[n - 1] - ema_slow[n - 1]
    candle_time = times[n - 1]
    price = closes[n - 1]

    key = f"{SYMBOL}|{INTERVAL}|{FAST_PERIOD}|{SLOW_PERIOD}"
    state = load_state()

    if state.get(key) == candle_time:
        print(f"Candela {candle_time} già valutata per {key}, nessuna azione.")
        return

    state[key] = candle_time
    save_state(state)

    print(
        f"{SYMBOL} {INTERVAL} | candela {candle_time} | prezzo {price:.5f} | "
        f"EMA{FAST_PERIOD}={ema_fast[n-1]:.5f} EMA{SLOW_PERIOD}={ema_slow[n-1]:.5f}"
    )

    if diff_prev <= 0 and diff_last > 0:
        send_telegram(
            f"📈 {SYMBOL} ({INTERVAL}): incrocio RIALZISTA\n"
            f"EMA{FAST_PERIOD} ha superato EMA{SLOW_PERIOD}\n"
            f"Candela: {candle_time}\nPrezzo: {price:.5f}"
        )
    elif diff_prev >= 0 and diff_last < 0:
        send_telegram(
            f"📉 {SYMBOL} ({INTERVAL}): incrocio RIBASSISTA\n"
            f"EMA{FAST_PERIOD} ha rotto sotto EMA{SLOW_PERIOD}\n"
            f"Candela: {candle_time}\nPrezzo: {price:.5f}"
        )
    else:
        print("Nessun incrocio su questa candela.")


if __name__ == "__main__":
    main()
