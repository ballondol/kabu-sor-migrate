"""
migrate.py のテスト — 主要な検出パターンを確認
"""
import tempfile
from pathlib import Path
from migrate import scan_file, Finding


def write_tmp(content: str) -> Path:
    f = tempfile.NamedTemporaryFile(suffix='.py', mode='w', delete=False, encoding='utf-8')
    f.write(content)
    f.close()
    return Path(f.name)


def test_json_double_quote():
    p = write_tmp('payload = {"exchange": "TSE", "qty": 100}\n')
    findings = scan_file(p)
    assert len(findings) == 1
    assert 'SOR' in findings[0].suggestion


def test_kwarg_single_quote():
    p = write_tmp("order(exchange='TSE', price=1500)\n")
    findings = scan_file(p)
    assert len(findings) == 1


def test_numeric_code():
    p = write_tmp('params = {"exchange": 1, "side": "2"}\n')
    findings = scan_file(p)
    assert len(findings) == 1
    assert '"exchange": 9' in findings[0].suggestion


def test_exchange_type_enum():
    p = write_tmp('exchange=ExchangeType.TSE\n')
    findings = scan_file(p)
    assert len(findings) == 1
    assert 'ExchangeType.SOR' in findings[0].suggestion


def test_pascal_case_numeric():
    p = write_tmp('payload = {"Exchange": 1, "Side": "2"}\n')
    findings = scan_file(p)
    assert len(findings) == 1
    assert '"Exchange": 9' in findings[0].suggestion


def test_no_false_positive():
    p = write_tmp('# already migrated\nexchange="SOR"\n')
    findings = scan_file(p)
    assert len(findings) == 0


def test_multiline():
    code = '''
send_order(
    password="xxxx",
    exchange="TSE",
    symbol="1234",
)
'''
    p = write_tmp(code)
    findings = scan_file(p)
    assert len(findings) == 1


if __name__ == '__main__':
    tests = [
        test_json_double_quote,
        test_kwarg_single_quote,
        test_numeric_code,
        test_pascal_case_numeric,
        test_exchange_type_enum,
        test_no_false_positive,
        test_multiline,
    ]
    passed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"  FAIL {t.__name__}: {e}")
    print(f"\n{passed}/{len(tests)} passed")
