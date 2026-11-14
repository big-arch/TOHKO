"""Check published HTML local links/assets; no network or third-party packages."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote

ROOT = Path(__file__).resolve().parents[1] / 'tights-guide'
errors = []

class Links(HTMLParser):
    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key not in ('href', 'src') or not value:
                continue
            url = urlsplit(value)
            if url.scheme or url.netloc or not url.path:
                continue
            target = (self.path.parent / unquote(url.path)).resolve()
            if not target.is_relative_to(ROOT.resolve()) or not target.exists():
                errors.append(f'{self.path.name}: missing local target {value}')

pages = list(ROOT.glob('*.html'))
for path in pages:
    parser = Links()
    parser.path = path
    parser.feed(path.read_text(encoding='utf-8'))
if errors:
    raise SystemExit('\n'.join(errors))
print(f'PASS: local links and assets in {len(pages)} HTML pages')
