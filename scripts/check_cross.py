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
        print("Telegram non configurato, salto invio:")
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


def is_market_open():
    url = f"https://api.twelvedata.com/quote?symbol={SYMBOL}&apikey={API_KEY}"
    try:
        resp = requests.get(url, timeout=15)
        data = resp.json()
    except requests.RequestException as e:
        print("Errore di rete durante il controllo market state:", e)
        return None

    if "is_market_open" in data:
        return bool(data["is_market_open"])

    print("Campo is_market_open non presente nella risposta /quote:", data)
    return None


def main():
    if not API_KEY:
        print("Manca TWELVE_DATA_API_KEY.")
        sys.exit(1)

    market_open = is_market_open()
    if market_open is False:
        print(f"Mercato chiuso per {SYMBOL} in questo momento: nessun controllo effettuato.")
        return

    outputsize = max(SLOW_PERIOD * 4, 300)
    url = (
        "https://api.twelvedata.com/time_series"
        f"?symbol={SYMBOL}&interval={INTERVAL}&outputsize={outputsize}"
        f"&timezone=UTC&apikey={API_KEY}"
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

    diff_last = ema_fast[n - 1] - ema_slow[n - 1]
    candle_time = times[n - 1]
    price = closes[n - 1]
    current_sign = 1 if diff_last > 0 else (-1 if diff_last < 0 else 0)

    key = f"{SYMBOL}|{INTERVAL}|{FAST_PERIOD}|{SLOW_PERIOD}"
    state = load_state()
    entry = state.get(key)
    if not isinstance(entry, dict):
        entry = None

    print(
        f"{SYMBOL} {INTERVAL} | mercato aperto: {market_open} | candela {candle_time} | "
        f"prezzo {price:.5f} | EMA{FAST_PERIOD}={ema_fast[n-1]:.5f} EMA{SLOW_PERIOD}={ema_slow[n-1]:.5f} | "
        f"verso attuale: {'sopra' if current_sign > 0 else 'sotto' if current_sign < 0 else 'uguale'}"
    )

    if entry is None:
        state[key] = {"time": candle_time, "sign": current_sign}
        save_state(state)
        print("Prima esecuzione (o formato precedente non compatibile): verso salvato, nessun avviso.")
        return

    if entry.get("time") == candle_time:
        print(f"Candela {candle_time} già valutata, nessuna azione.")
        return

    prev_sign = entry.get("sign", 0)
    state[key] = {"time": candle_time, "sign": current_sign}
    save_state(state)

    if prev_sign != 0 and current_sign != 0 and prev_sign != current_sign:
        if current_sign > 0:
            send_telegram(
                f"📈 {SYMBOL} ({INTERVAL}): incrocio RIALZISTA\n"
                f"EMA{FAST_PERIOD} ha superato EMA{SLOW_PERIOD}\n"
                f"Rilevato alla candela: {candle_time}\nPrezzo: {price:.5f}"
            )
        else:
            send_telegram(
                f"📉 {SYMBOL} ({INTERVAL}): incrocio RIBASSISTA\n"
                f"EMA{FAST_PERIOD} ha rotto sotto EMA{SLOW_PERIOD}\n"
                f"Rilevato alla candela: {candle_time}\nPrezzo: {price:.5f}"
            )
    else:
        print("Nessun cambio di verso da rilevare.")


if __name__ == "__main__":
    main()
