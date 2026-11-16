"""Fetch the fixed source list; preserve deployed entries during upstream outages."""
import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from news_feed import collect
from news_editorial import apply_editorial
from news_ai import preserve_generated

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'tights-guide/data'

class FetchError(OSError):
    def __init__(self,status):super().__init__('Source unavailable');self.status=status

def fetch_url(url):
    result=subprocess.run(['curl','--fail','--location','--compressed','--silent','--show-error',
        '--proto','=https','--proto-redir','=https','--connect-timeout','10','--max-time','30',
        '--max-filesize','8000000','--write-out','\n%{http_code}',
        '--user-agent','TONKO-News/1.0 (+https://big-arch.github.io/TOHKO/)',url],
        capture_output=True,timeout=40)
    body,_,code=result.stdout.rpartition(b'\n')
    status=int(code) if code.isdigit() else 0
    if result.returncode: raise FetchError(status)
    if len(body)>8_000_000: raise ValueError('Response too large')
    return body

def restore_previous(seed,fetch):
    try:raw=fetch('https://big-arch.github.io/TOHKO/data/news.json')
    except FetchError as error:
        if error.status==404:
            print('No public news snapshot yet (404); bootstrapping repository snapshot.')
            return seed
        raise
    deployed=json.loads(raw)
    if deployed.get('version')!=1 or not isinstance(deployed.get('items'),list) or not isinstance(deployed.get('sources'),list):
        raise ValueError('Invalid published snapshot; refusing to replace live news')
    return deployed

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--deployed',action='store_true',help='Restore previous public snapshot before collection')
    parser.add_argument('--cache',type=Path,help='Offline fixture directory; not used for production freshness')
    args=parser.parse_args()
    sources=json.loads((DATA/'news-sources.json').read_text(encoding='utf-8'))
    target=DATA/'news.json'
    previous=json.loads(target.read_text(encoding='utf-8')) if target.exists() else {}
    if args.deployed:
        # Do not replace accumulated live history with an older repository seed on network failure.
        previous=restore_previous(previous,fetch_url)
    def fetch(source):
        if args.cache:
            files={'google':'google.xml','snag':'snag.atom','swedish':'swedish.atom','whowhatwear':'whowhatwear.xml','fashionunited':'fashionunited.xml','bracatus':'bracatus.xml'}
            return (args.cache/files[source['id']]).read_bytes()
        return fetch_url(source['url'])
    result=collect(sources,previous,fetch,datetime.now(timezone.utc))
    preserve_generated(result,previous)
    apply_editorial(result)
    if args.cache:
        # Offline test runs must not impersonate a successful network check.
        result['checkedAt']=None;result['lastSuccessfulAt']=None
        for source in result['sources']: source['lastSuccessfulAt']=None
    temp=target.with_suffix('.tmp')
    temp.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');temp.replace(target)
    for source in result['sources']: print(source['name']+': '+source['status'])
    print('Headlines:',len(result['items']))
    # First deployment without any source/data must fail visibly.
    if not result['items'] and not result['lastSuccessfulAt'] and not args.cache: raise SystemExit('No verified news snapshot available')

if __name__=='__main__':main()
