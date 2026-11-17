"""Register verified channels and import individually reviewed release-16 videos.

The public deployed catalogue is restored before any write. Only official
thumbnail bytes are copied; publication timestamps come from each channel Atom.
"""
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "tights-guide/data"
sys.path.insert(0, str(ROOT / "scripts"))
from video_feed import FetchError, TextParser, date, identity, plain, stamp, validate_config
spec = importlib.util.spec_from_file_location("updater16", ROOT / "scripts/update-videos.py")
updater = importlib.util.module_from_spec(spec)
spec.loader.exec_module(updater)

SOURCES = [
    ("PoppyAttic", "poppy-attic-youtube", "Poppy Attic", "en"),
    ("Dashadaiz", "dasha-daiz-youtube", "Dasha Daiz", "en"),
    ("funkyredfoxx", "funkyredfox-youtube", "FunkyRedFox", "ru"),
    ("FunhoseStudios", "funhose-studios-youtube", "Funhose Studios", "en"),
    ("legsbylayla", "legs-by-layla-youtube", "Legs by Layla", "en"),
    ("peytonkinsly", "peyton-kinsly-youtube", "Peyton Kinsly", "en"),
    ("OonaLinna", "oona-linna-youtube", "OonaLinna", "en"),
]

# Selection is based on the individual official title, Atom description and
# reviewed official preview, not on a judgement about the author's profile.
REVIEWED = [
    ("legslavish", "iayHHSfIiKg", ["reviews", "styling"], "Сетка в образе: обзор Lexi", "Архив Legslavish: Lexi показывает узорчатую сетку с юбкой и туфлями. Короткий авторский обзор из декабря 2022 года.", "en", True),
    ("PoppyAttic", "5Z_E3EFnEUM", ["styling", "choice"], "Красные чулки: сочетание двух слоёв", "Poppy Attic показывает сочетание красных и чёрных чулок и изменение цвета при наложении прозрачной ткани.", "en", False),
    ("PoppyAttic", "If8WhJwiYsM", ["styling"], "Нейлон и узорчатые гольфы: сочетание слоёв", "Короткий разбор Poppy Attic: длинные узорчатые гольфы поверх нейлона в образе с клетчатой юбкой.", "en", False),
    ("PoppyAttic", "RtnZIiNb7mo", ["styling", "choice"], "Телесные оттенки: как сочетать два слоя чулок", "Poppy Attic сравнивает прозрачность и блеск двух телесных оттенков. Слово nude в исходном названии обозначает цвет изделия.", "en", False),
    ("Dashadaiz", "O3-nEUl9bFs", ["reviews", "tryon", "choice"], "Cecilia de Rafael Ibiza Dotty: мелкий горошек, 20 DEN", "Dasha Daiz примеряет матовые полупрозрачные колготки с мелким горошком и рассматривает, как рисунок смотрится в образе.", "en", False),
    ("Dashadaiz", "eR21-yHN7cA", ["reviews", "tryon", "styling"], "Calzedonia Longuette: обзор плотной модели", "Dasha Daiz показывает чёрные матовые колготки Longuette 70 DEN с фигурной деталью у колена и сочетание с платьем.", "en", False),
    ("Dashadaiz", "N4gBqi18clk", ["reviews", "choice", "styling"], "Oroblu All Colors 50 Peony: розовый в гардеробе", "Обзор розовых колготок Oroblu 50 DEN: автор обсуждает посадку, пояс, прозрачность и цвет при дневном свете.", "en", False),
    ("Dashadaiz", "0JYamXw7jiQ", ["reviews", "tryon", "styling"], "Бордовые колготки на осень: плотные или прозрачные", "Dasha Daiz сравнивает плотные Primark и прозрачные Calzedonia в горошек в одном осеннем образе.", "en", False),
    ("funkyredfoxx", "AY72V-uDWnI", ["styling", "choice"], "Кружевные колготки осенью: два слоя", "FunkyRedFox показывает, как сочетать кружевную фактуру с дополнительным слоем в прохладную погоду.", "ru", False),
    ("funkyredfoxx", "CZYpf9iATaw", ["reviews", "styling"], "Голубые колготки: осенний образ для офиса", "FunkyRedFox рассматривает голубые колготки с Temu и подбирает сочетание с водолазкой, юбкой и туфлями.", "ru", False),
    ("funkyredfoxx", "wx3TPfV7mGI", ["styling", "choice"], "Красный и чёрный: эксперимент с наслоением", "FunkyRedFox сочетает две пары колготок разного цвета и плотности, чтобы получить эффект внутреннего красного оттенка.", "ru", False),
    ("FunhoseStudios", "7aAdEV-V2yc", ["reviews", "tryon"], "Узорчатые колготки Primark: примерка", "Blossom на канале Funhose Studios показывает узорчатые колготки Primark и делится впечатлениями о рисунке и посадке.", "en", False),
    ("FunhoseStudios", "XcOu7MbJpwA", ["reviews", "choice"], "Love Your Legs и CDR Super Lucido: сравнение", "Funhose Studios сравнивает бюджетную модель Love Your Legs с CDR Super Lucido. Указанные в оригинале цены относятся к моменту записи.", "en", False),
    ("FunhoseStudios", "V--1r2RysSc", ["reviews", "choice"], "Колготки 40 DEN: поиск альтернативы Wolford Neon", "Blossom и Gabrielle сравнивают блестящую модель 40 DEN с Wolford Neon 40. Это авторское сравнение, а не лабораторный тест.", "en", False),
    ("legsbylayla", "pSNv4IEC1zc", ["reviews"], "Fiore из The Tight Spot: короткий обзор", "Legs by Layla показывает упаковку Fiore и знакомит с моделью из The Tight Spot в коротком авторском обзоре.", "en", False),
    ("legsbylayla", "tYoCQxDY0lI", ["tryon", "reviews"], "Limerence M: примерка блестящих колготок", "Legs by Layla примеряет несколько блестящих моделей Limerence M. В исходном описании автор отмечает, что изделия предоставлены брендом.", "en", False),
    ("legsbylayla", "b9X7XiQoZ44", ["styling", "tryon"], "Образы для рождественских ярмарок", "Legs by Layla собирает несколько образов с колготками, юбками, платьями и обувью и сравнивает варианты сочетаний.", "en", False),
    ("peytonkinsly", "Y-S28ALI3ZE", ["styling", "tryon"], "Блестящие чёрные легинсы и топ: вечерний образ", "Peyton Kinsly показывает сочетание легинсов из материала под кожу и короткого топа SlinkyStylez и обсуждает варианты стилизации.", "en", False),
]


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    now = datetime.now(timezone.utc)
    evidence = json.loads((ROOT / "qa/video16-research.json").read_text("utf-8"))
    channels = {c["handle"]: c for c in evidence["channels"]}
    records = {v["id"]: v for v in evidence["videos"]}
    config = json.loads((DATA / "video-sources.json").read_text("utf-8"))
    existing_sources = {s["id"] for s in config["sources"]}
    for handle, slug, name, language in SOURCES:
        if slug in existing_sources:
            continue
        channel = channels[handle]
        channel_id = channel["channelId"]
        assert channel["feed"]["channelId"] in {channel_id, channel_id[2:]}
        entries = channel["feed"]["entries"]
        sample = next(records[e["id"]] for e in entries if records.get(e["id"], {}).get("oembed"))
        author_url = sample["oembed"]["author_url"]
        assert author_url.casefold().rstrip("/") in {channel["url"].casefold(), "https://www.youtube.com/channel/" + channel_id.lower()}
        config["sources"].append(dict(id=slug, name=name, kind="youtube-atom", channelId=channel_id,
            url=channel["feed"]["url"], authorUrls=sorted({channel["url"], author_url, "https://www.youtube.com/channel/" + channel_id}),
            profile="fashion-review", language=language, verifiedAt=now.date().isoformat(), verificationUrl=channel["url"],
            verificationVideo=sample["url"]))
    validate_config(config)
    fetch = updater.Fetcher(config)
    def public_fetch(url, limit=4_000_000):
        # Local one-off restoration only: retry a connect timeout, never an
        # access denial, throttling, CAPTCHA or authentication response.
        for attempt in range(3):
            try:
                return fetch(url, limit)
            except FetchError as error:
                if error.status != 0 or attempt == 2:
                    raise
                print("Transient connection failure; retry", attempt + 1, flush=True)
    previous = updater.validate_catalog(json.loads((DATA / "videos.json").read_text("utf-8")))
    previous, live_state = updater.restore_previous(previous, public_fetch)
    baseline_path = ROOT / "qa/video16-live-baseline.json"
    if not baseline_path.exists():
        updater.atomic_write(baseline_path, (json.dumps(dict(checkedAt=stamp(now), total=len(previous),
            ids=[v["id"] for v in previous]), ensure_ascii=False, indent=2) + "\n").encode())
    for item in previous:
        target = ROOT / "tights-guide" / item["thumbnail"]
        if item.get("addedBy") == "feed" and not target.is_file():
            print("Restore published preview", item["id"], flush=True)
            raw = public_fetch(updater.PUBLIC + item["thumbnail"], limit=8_000_000)
            assert updater.image_extension(raw) == target.suffix
            updater.atomic_write(target, raw)

    old_ids = {v["id"] for v in previous}
    source_by_handle = {handle: slug for handle, slug, *_ in SOURCES}
    added = []
    for handle, ident, topics, title, description, language, archive in REVIEWED:
        if ident in old_ids:
            continue
        record, channel = records[ident], channels[handle]
        embed = record["oembed"]
        entry = next(e for e in channel["feed"]["entries"] if e["id"] == ident)
        assert entry["channelId"] == channel["channelId"]
        published = date(entry["publishedAt"], now)
        assert published is not None
        parser = TextParser()
        parser.feed(embed["html"])
        assert embed["type"] == "video" and any(identity(url) and identity(url)[:2] == ("youtube", ident) for url in parser.embeds)
        assert embed["author_url"].casefold().rstrip("/") == channel["url"].casefold()
        assert embed["thumbnail_url"].startswith("https://i.ytimg.com/")
        raw = (ROOT / record["previewPath"]).read_bytes()
        thumbnail = "assets/videos-new/" + ident + updater.image_extension(raw)
        updater.atomic_write(ROOT / "tights-guide" / thumbnail, raw)
        item = dict(id=ident, provider="youtube", title=title, originalTitle=plain(embed["title"], 200),
            description=description, topics=topics, language=language,
            kind="Архив · Авторское видео" if archive else "Авторское видео", author=plain(embed["author_name"], 100),
            authorUrl=embed["author_url"], channelId=channel["channelId"], url=record["url"], thumbnail=thumbnail,
            thumbnailSource=embed["thumbnail_url"], thumbnailWidth=embed["thumbnail_width"], thumbnailHeight=embed["thumbnail_height"],
            addedBy="curated", checked=now.date().isoformat(), embedCheckedAt=stamp(now), embedStatus="oembed",
            sourceUrl=record["url"], publishedAt=stamp(published), dateStatus="verified", dateSource="youtube:atom.published",
            dateVerificationUrl=record["url"])
        if archive:
            item["archive"] = True
        if handle in source_by_handle:
            item["sourceId"] = source_by_handle[handle]
        previous.append(item)
        added.append(ident)
    updater.validate_catalog(previous)
    assert all((ROOT / "tights-guide" / v["thumbnail"]).is_file() for v in previous)
    for filename, value in (("video-sources.json", config), ("videos.json", previous), ("video-feed-state.json", live_state)):
        updater.atomic_write(DATA / filename, (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode())
    print("Preserved baseline:", json.loads(baseline_path.read_text("utf-8"))["total"])
    print("Sources:", len(config["sources"]), "manually reviewed added:", len(added), "catalogue:", len(previous))
    print("Added IDs:", ", ".join(added))


if __name__ == "__main__":
    main()
