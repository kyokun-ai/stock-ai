from flask import Flask, render_template, request, jsonify
import math
import pandas as pd
import yfinance as yf

app = Flask(__name__)


def normalize_symbol(raw: str) -> str:
    s = (raw or '').strip().upper()
    if s.isdigit() and len(s) == 4:
        return f"{s}.T"
    return s


def rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, float('nan'))
    return 100 - (100 / (1 + rs))


def analyze(symbol: str):
    ticker = yf.Ticker(symbol)
    df = ticker.history(period='1y', interval='1d', auto_adjust=True)
    if df.empty or len(df) < 60:
        raise ValueError('十分な株価データを取得できませんでした。銘柄コードを確認してください。')

    close = df['Close']
    volume = df['Volume']
    ma5 = close.rolling(5).mean()
    ma25 = close.rolling(25).mean()
    ma75 = close.rolling(75).mean()
    rsi14 = rsi(close, 14)
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    vol20 = volume.rolling(20).mean()

    latest = df.iloc[-1]
    price = float(latest['Close'])
    score = 50
    reasons = []

    if price > ma25.iloc[-1]:
        score += 10; reasons.append('株価が25日移動平均線を上回っています。')
    else:
        score -= 10; reasons.append('株価が25日移動平均線を下回っています。')

    if ma5.iloc[-1] > ma25.iloc[-1]:
        score += 10; reasons.append('5日線が25日線を上回る短期上昇トレンドです。')
    else:
        score -= 8; reasons.append('5日線が25日線を下回っています。')

    if not math.isnan(ma75.iloc[-1]):
        if ma25.iloc[-1] > ma75.iloc[-1]:
            score += 8; reasons.append('25日線が75日線を上回っています。')
        else:
            score -= 6; reasons.append('25日線が75日線を下回っています。')

    rv = float(rsi14.iloc[-1])
    if 45 <= rv <= 65:
        score += 8; reasons.append('RSIは過熱感が比較的小さい範囲です。')
    elif rv >= 75:
        score -= 10; reasons.append('RSIは買われ過ぎ水準です。')
    elif rv <= 30:
        score += 3; reasons.append('RSIは売られ過ぎ水準です。反発余地を監視します。')

    if macd.iloc[-1] > signal.iloc[-1]:
        score += 9; reasons.append('MACDがシグナルを上回っています。')
    else:
        score -= 7; reasons.append('MACDがシグナルを下回っています。')

    if vol20.iloc[-1] and latest['Volume'] > vol20.iloc[-1] * 1.3:
        score += 5; reasons.append('出来高が20日平均より増加しています。')

    score = max(0, min(100, int(round(score))))
    if score >= 70:
        verdict = '上昇優勢'
    elif score >= 55:
        verdict = 'やや強気'
    elif score >= 45:
        verdict = '中立'
    elif score >= 30:
        verdict = 'やや弱気'
    else:
        verdict = '下落警戒'

    try:
        info = ticker.info or {}
        name = info.get('longName') or info.get('shortName') or symbol
    except Exception:
        name = symbol

    return {
        'symbol': symbol,
        'name': name,
        'price': round(price, 2),
        'score': score,
        'verdict': verdict,
        'rsi': round(rv, 1),
        'ma5': round(float(ma5.iloc[-1]), 2),
        'ma25': round(float(ma25.iloc[-1]), 2),
        'ma75': round(float(ma75.iloc[-1]), 2) if not math.isnan(ma75.iloc[-1]) else None,
        'macd': round(float(macd.iloc[-1]), 3),
        'signal': round(float(signal.iloc[-1]), 3),
        'reasons': reasons,
        'chart': [
            {'date': idx.strftime('%Y-%m-%d'), 'close': round(float(v), 2)}
            for idx, v in close.tail(90).items()
        ]
    }


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/analyze')
def api_analyze():
    symbol = normalize_symbol(request.args.get('symbol', ''))
    if not symbol:
        return jsonify({'error': '銘柄コードを入力してください。'}), 400
    try:
        return jsonify(analyze(symbol))
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'app': 'stock-ai-v1'})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
