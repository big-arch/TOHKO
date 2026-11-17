"""Refresh the public, dated USD/RUB display rate without credentials or paid APIs."""
import argparse
import json
from pathlib import Path
import subprocess
from exchange_rates import preferred_rate, refresh_rate

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / 'tights-guide/data/exchange-rate.json'
PUBLIC = 'https://big-arch.github.io/TOHKO/data/exchange-rate.json'


def fetch(url):
    result = subprocess.run(['curl', '--fail', '--silent', '--show-error', '--location',
        '--proto', '=https', '--proto-redir', '=https', '--connect-timeout', '10', '--max-time', '25',
        '--max-filesize', '1000000', '--user-agent', 'TONKO-Catalog/1.0 (+https://big-arch.github.io/TOHKO/)', url],
        capture_output=True, timeout=30)
    if result.returncode:
        raise OSError('Rate source request failed')
    return result.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--deployed', action='store_true')
    parser.add_argument('--force', action='store_true')
    args = parser.parse_args()
    seed = json.loads(TARGET.read_text('utf-8')) if TARGET.exists() else None
    published = None
    if args.deployed:
        try:
            published = json.loads(fetch(PUBLIC))
        except (OSError, ValueError, subprocess.TimeoutExpired):
            print('Published rate unavailable; validating the local reference snapshot.')
    previous = preferred_rate(seed, published)
    try:
        rate, status, error = refresh_rate(previous, fetch, force=args.force)
    except subprocess.TimeoutExpired:
        if previous is None:
            raise
        rate, status, error = previous, 'retained', 'TimeoutExpired'
    temp = TARGET.with_suffix('.tmp')
    temp.write_text(json.dumps(rate, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temp.replace(TARGET)
    print(f'USD/RUB reference rate: {status}; effective date {rate["date"]}; checked {rate["checkedAt"]}')
    if error:
        print('::warning::Exchange rate source unavailable; the previous rate and its date were retained.')


if __name__ == '__main__':
    main()
