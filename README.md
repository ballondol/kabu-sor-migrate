# kabu-sor-migrate

kabu STATION API **Ver5.41 (2026-05-16) 破壊的変更**対応ツール

Ver5.41 で市場コード `TSE (1)` が廃止されました。既存の Python コードは **今すぐ** 修正が必要です。

---

## 何が変わったか

| | 変更前 | 変更後 |
|---|---|---|
| 市場コード | `"Exchange": 1` (`"TSE"`) | `"Exchange": 9` (`"SOR"`) または `27` (`"TSE+"`) |
| 影響 | 発注・板照会 等 exchange を指定する全 API | |
| リリース日 | Ver5.41 — 2026-05-16 | |

### SOR と TSE+ どちらを選ぶか

| | SOR (`9`) | TSE+ (`27`) |
|---|---|---|
| 説明 | 複数市場を横断して最良価格で執行 | 東証を優先して執行 |
| 推奨 | **通常はこちら** (eスマート証券 手数料無料化対応) | 東証指定が必要な場合のみ |

> 参考: kabu STATION API [Issue #1186](https://github.com/kabucom/kabusapi/issues/1186)

---

## インストール

Python 3.9 以上。追加ライブラリ不要。

```bash
git clone https://github.com/ballondol/kabu-sor-migrate
cd kabu-sor-migrate
```

---

## 使い方

### 1. 診断 — どこを直すか確認

```bash
# ファイル単体
python migrate.py diagnose your_kabu_script.py

# フォルダ全体
python migrate.py diagnose src/
```

出力例:
```
============================================================
⚠️  kabu STATION API Ver5.41 SOR移行 診断結果
============================================================
対象: your_kabu_script.py
検出件数: 2 件

📄 your_kabu_script.py
  行    10 [numeric JSON PascalCase]
    現在: "Exchange": 1,
    推奨: "Exchange": 9,
  行    26 [JSON lowercase]
    現在: "exchange": "TSE"
    推奨: "exchange": "SOR"
```

### 2. 自動修正

```bash
python migrate.py fix your_kabu_script.py
```

- 元ファイルを `.bak` にバックアップしてから修正します
- 修正後は必ず動作確認してください

---

## 検出パターン

以下の記述をすべて検出します:

```python
# JSON / dict スタイル (PascalCase / lowercase 両対応)
{"Exchange": "TSE"}   # -> {"Exchange": "SOR"}
{"exchange": "TSE"}   # -> {"exchange": "SOR"}
{"Exchange": 1}       # -> {"Exchange": 9}
{"exchange": 1}       # -> {"exchange": 9}

# キーワード引数スタイル
exchange="TSE"        # -> exchange="SOR"
exchange=1            # -> exchange=9

# ライブラリ定数スタイル
ExchangeType.TSE      # -> ExchangeType.SOR
Exchange.TSE          # -> Exchange.SOR
```

---

## テスト

```bash
python test_migrate.py
# 7/7 passed
```

---

## 注意事項

- 自動修正は正規表現ベースです。修正後は必ずバックテストまたは動作確認を行ってください
- **投資助言ではありません。** 本ツールはコード移行の補助のみを目的とします
- kabu STATION API の利用には [kabu.com 利用規定](https://kabu.com/kabucom/terms.html) への同意が必要です

---

## 関連リンク

- [kabu STATION API 公式](https://kabucom.github.io/kabusapi/ptal/)
- [Issue #1186 — Ver5.41 SOR移行 Q&A](https://github.com/kabucom/kabusapi/issues/1186)
- [ballondol/kabu-station-auto-relogin](https://github.com/ballondol/kabu-station-auto-relogin) — 関連OSS

---

## License

MIT
