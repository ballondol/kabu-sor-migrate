#!/usr/bin/env python3
"""
kabu-sor-migrate: kabu STATION API Ver5.41 SOR移行 自動診断 + 修正ツール

Ver5.41 (2026-05-16) 破壊的変更:
  廃止: exchange="TSE" (市場コード 1)
  移行先: exchange="SOR" (市場コード 9)  ← SOR最良執行
          exchange="TSE+" (市場コード 27) ← 東証優先

使い方:
  診断のみ:   python migrate.py diagnose path/to/your/script.py
  自動修正:   python migrate.py fix path/to/your/script.py
  フォルダ全体: python migrate.py diagnose src/
"""

import io
import re
import sys
import shutil
from pathlib import Path
from dataclasses import dataclass

# Windows cp932 対策
if sys.stdout.encoding and sys.stdout.encoding.lower() in ('cp932', 'cp1252', 'ascii'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# TSE(1) 検出パターン (文字列マッチング)
# kabu STATION API: JSONボディは PascalCase ("Exchange"), クエリ/kwarg は lowercase ("exchange") の混在あり
TSE_PATTERNS = [
    # 文字列値での指定 — PascalCase キー ("Exchange": "TSE")
    (r'"Exchange"\s*:\s*"TSE"',     '"Exchange": "SOR"',  'JSON PascalCase'),
    (r"'Exchange'\s*:\s*'TSE'",     "'Exchange': 'SOR'",  'dict PascalCase'),
    # 文字列値での指定 — lowercase キー ("exchange": "TSE")
    (r'"exchange"\s*:\s*"TSE"',     '"exchange": "SOR"',  'JSON lowercase'),
    (r"'exchange'\s*:\s*'TSE'",     "'exchange': 'SOR'",  'dict lowercase'),
    (r'exchange\s*=\s*"TSE"',       'exchange="SOR"',     'kwarg double quote'),
    (r"exchange\s*=\s*'TSE'",       "exchange='SOR'",     'kwarg single quote'),
    # 数値コードでの指定 — PascalCase
    (r'"Exchange"\s*:\s*1\b',       '"Exchange": 9',      'numeric JSON PascalCase'),
    (r"'Exchange'\s*:\s*1\b",       "'Exchange': 9",      'numeric dict PascalCase'),
    # 数値コードでの指定 — lowercase
    (r'"exchange"\s*:\s*1\b',       '"exchange": 9',      'numeric JSON lowercase'),
    (r"'exchange'\s*:\s*1\b",       "'exchange': 9",      'numeric dict lowercase'),
    (r'exchange\s*=\s*1\b',         'exchange=9',         'numeric kwarg'),
    # ExchangeType 定数 (kabusapi ライブラリ使用時)
    (r'ExchangeType\.TSE\b',        'ExchangeType.SOR',   'ExchangeType enum'),
    (r'Exchange\.TSE\b',            'Exchange.SOR',       'Exchange enum'),
]

@dataclass
class Finding:
    file: Path
    line_no: int
    line: str
    pattern_desc: str
    suggestion: str


def scan_file(path: Path) -> list[Finding]:
    findings = []
    try:
        text = path.read_text(encoding='utf-8')
    except Exception:
        return findings

    for lineno, line in enumerate(text.splitlines(), start=1):
        for pattern, replacement, desc in TSE_PATTERNS:
            if re.search(pattern, line):
                fixed = re.sub(pattern, replacement, line)
                findings.append(Finding(
                    file=path,
                    line_no=lineno,
                    line=line.rstrip(),
                    pattern_desc=desc,
                    suggestion=fixed.rstrip(),
                ))
                break  # 1行に複数パターンが重なる場合は最初の1件のみ

    return findings


def scan_target(target: str) -> list[Finding]:
    p = Path(target)
    if p.is_file():
        return scan_file(p)
    elif p.is_dir():
        all_findings = []
        for py_file in sorted(p.rglob('*.py')):
            all_findings.extend(scan_file(py_file))
        return all_findings
    else:
        print(f"[ERROR] {target} が見つかりません")
        return []


def cmd_diagnose(target: str):
    findings = scan_target(target)

    if not findings:
        print("✅ TSE(1) の使用箇所は見つかりませんでした。移行済みか、対象外のコードです。")
        return

    print(f"\n{'='*60}")
    print(f"⚠️  kabu STATION API Ver5.41 SOR移行 診断結果")
    print(f"{'='*60}")
    print(f"対象: {target}")
    print(f"検出件数: {len(findings)} 件\n")

    current_file = None
    for f in findings:
        if f.file != current_file:
            print(f"\n📄 {f.file}")
            current_file = f.file
        print(f"  行 {f.line_no:4d} [{f.pattern_desc}]")
        print(f"    現在: {f.line.strip()}")
        print(f"    推奨: {f.suggestion.strip()}")

    print(f"\n{'='*60}")
    print("💡 自動修正するには: python migrate.py fix <ファイルまたはフォルダ>")
    print()
    print("📌 SOR vs TSE+ の選択指針:")
    print("  SOR (コード9):  複数市場を横断して最良価格で執行 ← 通常はこちらを推奨")
    print("  TSE+ (コード27): 東証を優先して執行 ← 東証指定が必要な場合")
    print("  詳細: https://github.com/kabucom/kabusapi/blob/master/docs/")


def cmd_fix(target: str):
    findings = scan_target(target)

    if not findings:
        print("✅ 修正対象がありません。")
        return

    # ファイルごとにグループ化
    from itertools import groupby
    files_with_findings = {}
    for f in findings:
        files_with_findings.setdefault(f.file, []).append(f)

    print(f"\n{'='*60}")
    print(f"🔧 kabu STATION API Ver5.41 SOR移行 自動修正")
    print(f"{'='*60}\n")

    for file_path, file_findings in files_with_findings.items():
        # バックアップ
        backup = file_path.with_suffix('.py.bak')
        shutil.copy2(file_path, backup)

        text = file_path.read_text(encoding='utf-8')
        original = text

        for pattern, replacement, _ in TSE_PATTERNS:
            text = re.sub(pattern, replacement, text)

        if text != original:
            file_path.write_text(text, encoding='utf-8')
            print(f"✅ 修正完了: {file_path} ({len(file_findings)} 件)")
            print(f"   バックアップ: {backup}")
        else:
            print(f"⚠️  変更なし: {file_path}")

    print(f"\n修正後は必ず動作確認してください。")
    print(f"元に戻すには .bak ファイルをリストアしてください。")


def main():
    if len(sys.argv) < 3 or sys.argv[1] not in ('diagnose', 'fix'):
        print(__doc__)
        print("Usage: python migrate.py [diagnose|fix] <file_or_directory>")
        sys.exit(1)

    cmd = sys.argv[1]
    target = sys.argv[2]

    if cmd == 'diagnose':
        cmd_diagnose(target)
    elif cmd == 'fix':
        cmd_fix(target)


if __name__ == '__main__':
    main()
