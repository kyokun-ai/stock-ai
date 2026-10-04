# 株AI v1
日本株の日足テクニカル分析プロトタイプ。

## Render
- Runtime: Python 3
- Build: `pip install -r requirements.txt`
- Start: `gunicorn app:app`
- Plan: Free

## v1分析項目
- 5/25/75日移動平均
- RSI(14)
- MACD / Signal
- 出来高20日平均比較
- 総合スコア 0-100

重要な研究データはRender内に永続保存しない設計です。
