"""Save the site's validated published feed state as a periodic recovery snapshot."""
import argparse
import importlib.util
import json
from pathlib import Path
from news_publication import sync_publication
from exchange_rates import validate_rate

ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/'tights-guide'
PUBLIC='https://big-arch.github.io/TOHKO/'

def module(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/(name+'.py'))
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true',help='Validate public data without modifying local files')
    args=parser.parse_args()
    news_module=module('update-news');video_module=module('update-videos')
    news=news_module.restore_previous({},news_module.fetch_url)
    if not news.get('items') or len(news['items'])>400:raise ValueError('Invalid news snapshot')
    sync_publication(news)
    videos=video_module.validate_catalog(json.loads(news_module.fetch_url(PUBLIC+'data/videos.json')))
    state=json.loads(news_module.fetch_url(PUBLIC+'data/video-feed-state.json'))
    if state.get('version')!=1 or not isinstance(state.get('sources'),list):raise ValueError('Invalid source state')
    for video in videos:
        if video.get('addedBy')!='feed':continue
        target=SITE/video['thumbnail']
        if target.exists():continue
        raw=news_module.fetch_url(PUBLIC+video['thumbnail'])
        if video_module.image_extension(raw)!=target.suffix:raise ValueError('Invalid published image')
        if not args.check:video_module.atomic_write(target,raw)
    for name,data in [('news.json',news),('videos.json',videos),('video-feed-state.json',state)]:
        if not args.check:video_module.atomic_write(SITE/'data'/name,(json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    catalogue_module=module('collect-catalog18')
    if args.check:
        catalogue=json.loads(news_module.fetch_url(PUBLIC+'data/catalog.json'))
        if catalogue.get('version')!=1 or not catalogue.get('coverage',{}).get('complete') or not catalogue.get('items'):
            raise ValueError('Invalid published catalogue snapshot')
    else:
        catalogue,_=catalogue_module.restore_deployed(PUBLIC,SITE/'data/catalog.json')
    exchange=validate_rate(json.loads(news_module.fetch_url(PUBLIC+'data/exchange-rate.json')))
    if not args.check:video_module.atomic_write(SITE/'data/exchange-rate.json',(json.dumps(exchange,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    print(f'Recovery snapshot: {len(news["items"])} news records, {len(videos)} videos, {len(catalogue["items"])} catalogue models')

if __name__=='__main__':main()
