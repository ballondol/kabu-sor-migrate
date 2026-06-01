# Claude Code security-guidance plugin で kabu Bot の危険パターンを自動検出する

## はじめに

kabu STATION® API で Claude Code を使って株 Bot を開発していると、こんな不安を感じたことはありませんか？

- 「誤発注したらどうしよう」
- 「APIキーをうっかりログに出してしまいそう」
- 「本番とテスト環境を混同してしまいそう」

Claude Code には `security-guidance` という公式プラグインがあります。これを使うと、**コードを書きながらリアルタイムで危険なパターンを検出**し、警告を出してくれます。

この記事では、IT SE 20年の経験と kabu STATION® API の実運用から見えてきた **kabu Bot 固有の危険パターン 7選** を定義したカスタムルールセットを公開します。

---

## kabu Bot 固有のセキュリティリスク 7選

### 1. APIパスワード・トークンのログ漏洩

kabu STATION® API では `/auth` エンドポイントでトークンを取得し、以降のリクエストに `X-API-PASSWORD` ヘッダーで渡します。このトークンをうっかり `print()` やログに出してしまうと、口座への不正アクセスにつながります。

```python
# ❌ 危険
token = get_token()
print(f"取得したトークン: {token}")  # ← 絶対にやってはいけない

# ✅ 安全
token = get_token()
logger.info("トークン取得成功")  # 値は出力しない
```

### 2. 確認なしの自動発注

kabu STATION® API には**サンドボックス環境がありません**。すべてのAPI呼び出しは本番口座に直接影響します。発注APIを呼ぶ前には必ず確認プロセスを挟むべきです。

```python
# ❌ 危険
def buy_stock(symbol, qty, price):
    api.send_order(symbol=symbol, qty=qty, price=price)  # 即時発注

# ✅ 安全
def buy_stock(symbol, qty, price):
    print(f"発注確認: {symbol} × {qty}株 @ ¥{price:,}")
    if input("実行しますか? [yes/N]: ").lower() != "yes":
        print("キャンセルしました")
        return
    api.send_order(symbol=symbol, qty=qty, price=price)
```

### 3. 注文IDを確認しない取消し

注文取消し（`/kabusapi/cancelorder`）を「銘柄コード」や「状態」で実行しようとすると、意図しない注文をキャンセルするリスクがあります。

```python
# ❌ 危険
def cancel_all_orders(symbol):
    orders = api.get_orders(symbol=symbol)
    for order in orders:
        api.cancel_order(order_id=order["OrderID"])  # 全部キャンセル

# ✅ 安全
def cancel_specific_order(order_id: str):
    # 現在の注文一覧からOrderIDを確認してからキャンセル
    orders = api.get_orders()
    target = next((o for o in orders if o["OrderID"] == order_id), None)
    if target is None:
        raise ValueError(f"OrderID {order_id} が見つかりません")
    api.cancel_order(order_id=order_id)
```

### 4. WebSocket接続の無言切断

kabu STATION® API の WebSocket プッシュ配信は、アイドル状態や network interruption で**無言で切断**されることがあります。再接続ロジックがないと、価格データが古くなったまま Bot が動き続けます。

```python
# ❌ 危険
ws = websocket.create_connection(KABU_WS_URL)
while True:
    data = ws.recv()  # 切断されたら例外、再接続なし

# ✅ 安全
def connect_with_retry(max_retries=5):
    for attempt in range(max_retries):
        try:
            ws = websocket.create_connection(KABU_WS_URL)
            logger.warning(f"WebSocket接続成功 (試行 {attempt + 1}回目)")
            return ws
        except Exception as e:
            wait = 2 ** attempt
            logger.warning(f"WebSocket切断 (試行 {attempt + 1}回目): {e}. {wait}秒後に再接続")
            time.sleep(wait)
    raise ConnectionError("WebSocket再接続に失敗しました")
```

### 5. レート制限超過

kabu STATION® API は **10リクエスト/秒** のレート制限があります。ループ内でsleepなしにAPIを叩くと、HTTP 429 が返りさらに制限がかかることがあります。

```python
# ❌ 危険
for symbol in symbols:
    price = api.get_board(symbol)  # sleepなし

# ✅ 安全
for symbol in symbols:
    price = api.get_board(symbol)
    time.sleep(0.1)  # 10req/s以内に収める
```

### 6. レスポンス本文のまるごとログ

APIレスポンスには残高・保有株・注文情報などの機密データが含まれます。`response.text` をそのままログに出すと、ログファイルが機密情報の塊になります。

```python
# ❌ 危険
response = requests.post(url, headers=headers, json=body)
logger.debug(f"レスポンス: {response.text}")  # 機密データ丸出し

# ✅ 安全
response = requests.post(url, headers=headers, json=body)
logger.debug(f"ステータス: {response.status_code}")
if not response.ok:
    logger.error(f"APIエラー: {response.status_code} {response.reason}")
```

### 7. SOR設定の古いデフォルト値

eスマート証券は **2026年5月18日** より国内株式をSOR選択時に手数料無料化しました。古いコードに `SOR=False` がハードコードされていると、手数料を無駄に払い続けることになります。

```python
# ❌ 古いコード (手数料発生)
def send_order(symbol, qty, price):
    body = {
        "Symbol": symbol,
        "Qty": qty,
        "Price": price,
        "FrontOrderType": 20,
        "SOR": False,  # ← 古いデフォルト
    }

# ✅ 2026-05-18以降の正しい設定
def send_order(symbol, qty, price, sor=True):
    body = {
        "Symbol": symbol,
        "Qty": qty,
        "Price": price,
        "FrontOrderType": 20,
        "SOR": sor,  # デフォルトTrue (手数料無料)
    }
```

---

## Claude Code security-guidance plugin の設定方法

### インストール

```bash
# Claude Code セッション内で実行
/plugin install security-guidance@claude-plugins-official
/reload-plugins
```

マーケットプレイスが見つからない場合:
```bash
/plugin marketplace add anthropics/claude-plugins-official
```

### ルールファイルの配置

プラグインインストール後、`.claude/` ディレクトリに2種類のファイルを置きます。

```
your-kabu-project/
└── .claude/
    ├── claude-security-guidance.md   # モデルが読むテキストルール
    └── security-patterns.yaml        # パターンマッチングルール
```

---

## 公開したルールセット

上記の7パターンを実装したルールセットを kabu-sor-migrate リポジトリに追加しました。

**リポジトリ**: https://github.com/ballondol/kabu-sor-migrate

`.claude/claude-security-guidance.md` と `.claude/security-patterns.yaml` の2ファイルを自分の kabu プロジェクトにコピーして使えます。

### claude-security-guidance.md の概要

Claude Code のモデルが各コード編集時・コミット時にレビューする際に参照するルールです。
自然言語で「kabu APIのパスワードをログに出さない」「発注前に確認を取る」などを定義しています。

### security-patterns.yaml の概要

regex / substring マッチングで**モデル呼び出しなしに**瞬時に危険パターンを検出します。定義したパターンの例:

| ルール名 | 検出対象 | 警告内容 |
|---------|---------|---------|
| `kabu_api_password_hardcoded` | `X-API-PASSWORD` の文字列 | 環境変数から読み込むよう促す |
| `sendorder_without_confirm` | `/kabusapi/sendorder` の呼び出し | 発注前確認を促す |
| `bare_except` | `except:` の使用 | 具体的な例外クラスの指定を促す |
| `sor_false_default` | `SOR=False` の設定 | 2026-05-18以降のデフォルト変更を通知 |

---

## 動作の 3 レイヤー

| タイミング | 内容 |
|-----------|------|
| ファイル編集ごと | security-patterns.yaml でパターンマッチ（無料） |
| ターン終了ごと | git diff を Claude Opus がレビュー（有料） |
| git commit/push ごと | 深堀りレビュー（有料） |

パターンマッチングは無料で動くため、発注APIの呼び出しが含まれるたびに「確認を取ってください」という reminder を無料で表示できます。

---

## まとめ

kabu STATION® API には独特のリスクがあります:
- **サンドボックスなし**: テストも本番口座に直結
- **認証トークン管理**: ログやコードへの混入リスク
- **SOR設定**: 2026年5月以降の仕様変更対応

Claude Code の `security-guidance` plugin に kabu Bot 固有のルールセットを設定することで、コードを書きながらリアルタイムでこれらのリスクを検出できます。

ルールセットは MIT ライセンスで公開しています。kabu Bot 開発者の方にとって参考になれば幸いです。

---

## 関連記事

- [eスマート証券のSOR手数料無料化に対応するコードを自動移行する CLI ツール](https://qiita.com/ballondol/items/81be7a4f1f23f3c4f073)
- [Claude Code Skills の disallowed-tools を 5 パターンで安全に設計する](https://qiita.com/ballondol/items/d26b4c1159df75991dc8)
