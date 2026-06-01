# Security Guidance for kabu-sor-migrate / kabu Bot

This repository interacts with the kabu STATION® API (eスマート証券).
The following rules apply to all code edits in this project.

## 1. Authentication & Credentials

- **Never log `X-API-PASSWORD` header values** at any log level.
- **Never log API tokens** returned by `/auth` endpoints, even at DEBUG level.
- Load credentials from environment variables (`KABU_API_PASSWORD`, `KABU_ENDPOINT`) only.
  Never hardcode credentials in source files or configuration files.
- If you see credentials in plain text anywhere in the code, refuse to proceed and flag it immediately.

## 2. Order Placement Safety

- **Always confirm before placing an order.** Any code path that calls the order API
  (`/kabusapi/sendorder`, POST) must first display a human-readable summary
  (symbol, side, quantity, price) and wait for explicit user confirmation.
- **Validate quantity before calling the order API:**
  - quantity > 0
  - quantity ≤ user-defined MAX_ORDER_QTY (default: 100 shares)
  - quantity is an integer (no fractional shares)
- **Never call the order cancellation API (`/kabusapi/cancelorder`)** without
  confirming the exact `OrderID` from the current order list.
  Do not cancel by symbol or status alone.

## 3. Environment Isolation (Backtest vs. Live)

- The kabu STATION® API has no sandbox environment — all API calls affect real accounts.
- **Always check `KABU_ENV` environment variable before order placement:**
  - If `KABU_ENV != "live"`, raise an error and abort order placement.
- Never use hardcoded endpoint URLs; always use the environment variable `KABU_ENDPOINT`.
- Add a prominent comment near any order-related function: `# LIVE TRADING — no sandbox`.

## 4. WebSocket Connection

- The WebSocket push endpoint (`ws://localhost:18080/kabusapi/websocket`) drops silently
  on idle or network interruption. Always implement reconnection logic with exponential backoff.
- **Log WebSocket disconnections at WARNING level** (not DEBUG) so they are never missed.
- Never assume the WebSocket connection is alive without a heartbeat or recent message timestamp check.

## 5. Rate Limiting

- The kabu STATION® REST API enforces a rate limit of **10 requests per second**.
  Always add `time.sleep(0.1)` between consecutive API calls in loops.
- If an HTTP 429 response is received, wait at least 5 seconds before retrying.
- **Never implement a retry loop without a maximum retry count** (max: 5 retries).

## 6. Error Handling & Logging

- **Never include raw API response bodies in log output** — responses may contain
  sensitive position, balance, or order data.
- Always log the HTTP status code and a sanitized error message only.
- Wrap all API calls in try/except and handle `ConnectionError`, `Timeout`, and `HTTPError`
  separately. Do not use bare `except:`.

## 7. SOR (Smart Order Routing) Migration Checks

- This repository's primary purpose is to identify code that assumes old commission structures
  (pre-2026-05-18) and flag it for migration.
- Flag any hardcoded commission values or fee calculations.
- Flag any logic that assumes `SOR=False` as the default (the new default is `SOR=True`
  for eスマート証券 as of 2026-05-18).
