import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.request import urlopen, Request
import json
import math

PORT = int(os.environ.get("PORT", 8080))

BINANCE_API = (
    "https://api.binance.com/api/v3/klines"
    "?symbol=BTCUSDT&interval=1m&limit=50"
)


def get_candles():
    request = Request(
        BINANCE_API,
        headers={"User-Agent": "BALOCHFX/1.0"}
    )

    with urlopen(request, timeout=10) as response:
        data = json.loads(response.read().decode("utf-8"))

    candles = []

    for item in data:
        candles.append({
            "open": float(item[1]),
            "high": float(item[2]),
            "low": float(item[3]),
            "close": float(item[4])
        })

    return candles


def ema(values, period):
    if len(values) < period:
        return None

    multiplier = 2 / (period + 1)
    result = sum(values[:period]) / period

    for price in values[period:]:
        result = (price - result) * multiplier + result

    return result


def rsi(values, period=14):
    if len(values) <= period:
        return None

    gains = []
    losses = []

    for i in range(1, len(values)):
        change = values[i] - values[i - 1]

        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(gains)):
        avg_gain = ((avg_gain * (period - 1)) + gains[i]) / period
        avg_loss = ((avg_loss * (period - 1)) + losses[i]) / period

    if avg_loss == 0:
        return 100

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def analyze(candles):
    closes = [c["close"] for c in candles]

    current = candles[-1]
    previous = candles[-2]

    ema5 = ema(closes, 5)
    ema20 = ema(closes, 20)
    current_rsi = rsi(closes)

    score = 0

    # EMA trend
    if ema5 and ema20:
        if ema5 > ema20:
            score += 2
        elif ema5 < ema20:
            score -= 2

    # RSI momentum
    if current_rsi is not None:
        if current_rsi > 55:
            score += 1
        elif current_rsi < 45:
            score -= 1

    # Last completed candle direction
    if current["close"] > current["open"]:
        score += 1
    elif current["close"] < current["open"]:
        score -= 1

    # Previous candle confirmation
    if previous["close"] > previous["open"]:
        score += 1
    elif previous["close"] < previous["open"]:
        score -= 1

    if score >= 3:
        signal = "UP"
        emoji = "🟢"
    elif score <= -3:
        signal = "DOWN"
        emoji = "🔴"
    else:
        signal = "NEUTRAL"
        emoji = "🟡"

    body = abs(current["close"] - current["open"])
    candle_range = current["high"] - current["low"]

    if candle_range > 0:
        body_percent = (body / candle_range) * 100
    else:
        body_percent = 0

    if abs(score) >= 4:
        strength = "STRONG"
    elif abs(score) >= 2:
        strength = "MEDIUM"
    else:
        strength = "WEAK"

    return {
        "price": current["close"],
        "signal": signal,
        "emoji": emoji,
        "strength": strength,
        "score": score,
        "rsi": round(current_rsi, 2) if current_rsi else None,
        "ema5": round(ema5, 2) if ema5 else None,
        "ema20": round(ema20, 2) if ema20 else None,
        "candle": (
            "BULLISH"
            if current["close"] > current["open"]
            else "BEARISH"
            if current["close"] < current["open"]
            else "DOJI"
        ),
        "body_percent": round(body_percent, 1)
    }


class Handler(SimpleHTTPRequestHandler):

    def do_GET(self):

        if self.path == "/api/btc":

            try:
                candles = get_candles()
                result = analyze(candles)

                body = json.dumps(result).encode("utf-8")

                self.send_response(200)
                self.send_header(
                    "Content-Type",
                    "application/json"
                )
                self.send_header(
                    "Access-Control-Allow-Origin",
                    "*"
                )
                self.send_header(
                    "Content-Length",
                    str(len(body))
                )
                self.end_headers()

                self.wfile.write(body)

            except Exception as e:

                body = json.dumps({
                    "error": str(e)
                }).encode("utf-8")

                self.send_response(500)
                self.send_header(
                    "Content-Type",
                    "application/json"
                )
                self.send_header(
                    "Content-Length",
                    str(len(body))
                )
                self.end_headers()

                self.wfile.write(body)

            return

        super().do_GET()


server = ThreadingHTTPServer(
    ("", PORT),
    Handler
)

print(
    f"BALOCHFX server running on http://127.0.0.1:{PORT}"
)

server.serve_forever()
