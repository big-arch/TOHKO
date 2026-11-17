"""Reproducible release 15 source registration and reviewed archive import.

Reads the one-off evidence file. Uses only public oEmbed / official thumbnails;
does not download videos. Archive dates below are exact calendar dates from the
indexed original YouTube pages, except the explicitly identified Atom timestamp.
Unknown dates are omitted and visibly labelled by build-videos.py.
"""
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from video_feed import TextParser, identity, plain, stamp, validate_config
spec = importlib.util.spec_from_file_location("updater15", ROOT / "scripts/update-videos.py")
updater = importlib.util.module_from_spec(spec)
spec.loader.exec_module(updater)
DATA = ROOT / "tights-guide/data"
RESEARCH = ROOT / "qa/video15-research.json"

# Exact IDs from the public channel's RSS link and matching Atom root.
SOURCES = [
    ("svetlana-makarova", "UC1DZTK2DAylpWtucMcZSXOw", "Светлана Макарова", "ru", "fashion"),
    ("anastasia-odels", "UCtuUdhlMTAz9dleiMB3v58w", "Анастасия Оделс", "ru", "fashion"),
    ("liria-kholdina", "UC-sZ2H9Y6hCYkuHNTf7EpBQ", "Лирия Холдина · Dress to Impress", "ru", "fashion"),
    ("olga-delevsky", "UCVL-KVo_ZjQuP8VpwgABisQ", "Школа стиля Ольги Делевски", "ru", "fashion"),
    ("kseniya-shirshova", "UChBKPr6rRi2HY5d92sUxh2A", "Kseniya Shirshova", "ru", "fashion"),
    ("kerina-wang", "UCa9siXYE9McabZSTOkhnUtg", "Kerina Wang", "en", "fashion"),
    ("the-tight-spot", "UCdGZ5AxDylcpE8fW2cwmQBw", "TightsTV · The Tight Spot", "en", "fashion"),
    ("layla-fashion", "UCxL5Q1badukzLkDOF7hIuaA", "Layla Fashion", "en", "fashion"),
    ("sheertex", "UCi8Iy9BQyr3caO4mk7zKMnA", "Sheertex", "en", "fashion"),
    ("glamissima", "UCpLLCQlTQsN5B7kxp0GuutQ", "Glamissima", "original", "fashion"),
    ("asmr-fuyu", "UC98T-GUCry4ss7GPmqVc5Qg", "ASMR Fuyu", "original", "textile-asmr"),
    ("gentle-whispering", "UC6gLlIAnzg7eJ8VuXDCZ_vg", "Gentle Whispering ASMR", "original", "textile-asmr"),
    ("whispersred-asmr", "UC2nyigZS5YNDrCu_pih809w", "WhispersRed ASMR", "en", "textile-asmr"),
    ("asmr-cheeks", "UCWMhB_iUo7n5b0dkdby1Suw", "ASMR CHeeks", "ru", "textile-asmr"),
    ("bolshe-chem-stil", "UCCuqMOJ5jwGnh-SNQ72LnPw", "Больше чем стиль", "ru", "fashion"),
    ("annika-victoria", "UCqP8HosuK1VRD60wBaEEFtA", "Annika Victoria", "en", "fashion"),
    ("tinkerbell", "UC3LmX0VVBcQ35nJgKdLtrQQ", "Tinkerbell", "en", "fashion"),
    ("401-money-gang", "UC1W3dsKohMwDR4el0cYLeiQ", "401 Money Gang", "en", "fashion"),
    ("samantha-yonge", "UCt29z9MC_AG1MdPnKM6fOOQ", "Samantha Yonge", "en", "fashion"),
]

# Each description is an editorial summary, not a copy of a channel footer.
ARCHIVE = [
    ("G6m9vzvaGoc", "2024-08-24", "ru", ["styling", "choice"], "Цветные колготки: восемь сочетаний", "Светлана Макарова разбирает цветовые сочетания и место колготок в гардеробе. Архивный выпуск: примеры и рекомендации относятся к моменту съёмки."),
    ("yqTK5Gs0qmA", None, "ru", ["choice", "styling"], "Как выбирать, сочетать и носить колготки", "Анастасия Оделс — о выборе колготок и сочетании с одеждой. Архивный выпуск; точная дата публикации пока не подтверждена."),
    ("qlPJ4PhnNWo", "2021-09-24", "ru", ["choice", "styling"], "Колготки как часть образа", "Лирия Холдина разбирает капроновые, плотные и цветные модели. Взгляд стилиста из архива 2021 года."),
    ("yJ_D-39z7eg", "2021-02-25", "ru", ["choice", "styling"], "Гид по колготкам: архив 2021 года", "Школа стиля Ольги Делевски: телесные, чёрные, цветные колготки и принты. Упомянутые тренды относятся к 2021 году."),
    ("24E0r4MRLuI", "2015-10-30", "ru", ["styling", "choice"], "Пять образов с колготками: архив 2015 года", "Ксения Ширшова показывает сочетания для разных повседневных ситуаций. Архивный лукбук: ассортимент и модные оценки относятся к 2015 году."),
    ("I85twyDA_-g", None, "en", ["styling", "tryon"], "Пятнадцать образов с колготками", "Лукбук Kerina Wang: сочетания колготок, юбок, платьев и обуви. Архивный выпуск; точная дата публикации не подтверждена."),
    ("fVRy95vrAZ4", "2020-02-08", "en", ["styling", "tryon"], "Колготки в холодную погоду", "Kerina Wang показывает многослойные образы с обычными и узорчатыми колготками. Архив 2020 года; наличие вещей и цены могли измениться."),
    ("TVDNAIs4N7Q", "2024-11-12", "none", ["asmr"], "ASMR: шорох и растяжение ткани", "Luxe Mia ASMR исследует звучание нейлоновой ткани: шорох, растяжение и разрыв материала. Без речи и музыки; начните с комфортной громкости."),
    ("zu8UTjg3E4U", None, "ru", ["asmr"], "ASMR: прикосновения к ткани одежды", "ASMR CHeeks — звуки прикосновений и скретчинга по ткани. Архивная запись; точная дата публикации не подтверждена."),
    ("adj7nIdbrXc", "2017-12-14", "ru", ["styling", "choice"], "Цветные колготки: фрагмент вебинара", "Галина Галышина на канале «Больше чем стиль» разбирает цветные колготки в образе. Фрагмент вебинара из архива 2017 года."),
    ("jAovDlIn6CA", "2017-08-15", "en", ["making", "styling"], "Новая жизнь колготок: DIY и лукбук", "Annika Victoria показывает переделку колготок в носки и варианты сочетаний. Архивный выпуск серии Style Pile."),
    ("vbIbX589Idc", None, "en", ["reviews", "choice"], "Calzedonia Invisible 20 DEN: обзор", "Tinkerbell рассматривает бесшовную модель Invisible 20 Denier. Это впечатления автора; точная дата архивного выпуска не подтверждена."),
    ("Lhb91O9w5wk", "2026-01-19T16:56:50Z", "en", ["reviews"], "Сравнение прочности: тест в носке", "Автор канала 401 Money Gang сравнивает колготки в носке. Результаты отражают условия авторского теста и не заменяют характеристики производителя."),
    ("s5RVt62Scgc", None, "en", ["reviews", "tryon"], "Sheertex: авторский тест прочности", "Samantha Yonge проверяет колготки Sheertex и показывает примерку. Архивный обзор; точная дата публикации не подтверждена."),
    ("599LMnGLC9k", "2021-06-14", "en", ["asmr"], "ASMR: в магазине тканей", "Gentle Whispering показывает фактуры тюля, бархата, шифона и декоративных материалов. Спокойное знакомство со звуками и поверхностью ткани."),
    ("l790AoYh1HE", "2026-08-02", "en", ["asmr"], "ASMR: ткань, молнии и содержимое сумки", "WhispersRed исследует ткань сумки, звучание молний и небольших предметов. Видео с тихой речью из летней подборки автора."),
]


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    evidence = json.loads(RESEARCH.read_text("utf-8"))
    config = json.loads((DATA / "video-sources.json").read_text("utf-8"))
    fetch = updater.Fetcher(config)
    channels = evidence["channels"]
    # A transient retry lacked a page response, but the first public RSS link
    # had already resolved this exact ID. Preserve that confirmed identity.
    annika = next(c for c in channels if c["url"].endswith("/@AnnikaVictoria24"))
    if not annika.get("channelId"):
        annika["channelId"] = "UCqP8HosuK1VRD60wBaEEFtA"
        annika["verificationNote"] = "Public channel RSS link resolved during initial 2026-11-16 pass; retry timed out."
    now = datetime.now(timezone.utc)
    known_sources = {s["id"] for s in config["sources"]}
    for slug, channel_id, name, language, profile in SOURCES:
        ident = slug + "-youtube"
        if ident in known_sources:
            continue
        matches = [c for c in channels if c.get("channelId") == channel_id]
        assert matches, (slug, "missing channel evidence")
        urls = {c["url"] for c in matches}
        urls.add("https://www.youtube.com/channel/" + channel_id)
        # Channels supplied without an individual clip need an oEmbed author
        # sample as well as the public channel-ID / feed match.
        existing = [v for v in evidence["videos"] if v.get("oembed", {}).get("author_url") in urls]
        if not existing:
            entry = next((e for c in matches for e in c.get("feed", {}).get("entries", [])), None)
            if entry:
                endpoint = "https://www.youtube.com/oembed?url=https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3D" + entry["id"] + "&format=json"
                try:
                    embed = json.loads(fetch(endpoint))
                    urls.add(embed["author_url"])
                    matches[0]["sampleOembed"] = {"url": endpoint, "videoId": entry["id"], "authorUrl": embed["author_url"], "author": embed["author_name"], "title": embed["title"], "checkedAt": stamp(now)}
                except (OSError, ValueError, KeyError):
                    print("Sample oEmbed unavailable:", slug)
                    continue
        source = dict(id=ident, name=name, kind="youtube-atom", channelId=channel_id,
                      url="https://www.youtube.com/feeds/videos.xml?channel_id=" + channel_id,
                      authorUrls=sorted(urls), profile=profile, language=language,
                      verifiedAt=now.date().isoformat(), verificationUrl=matches[0]["url"])
        config["sources"].append(source)
    config["maxNewPerSource"] = 3
    order = {slug + "-youtube": index + 10 for index, (slug, *_rest) in enumerate(SOURCES)}
    config["sources"].sort(key=lambda source: order.get(source["id"], 0))
    validate_config(config)
    updater.atomic_write(DATA / "video-sources.json", (json.dumps(config, ensure_ascii=False, indent=2) + "\n").encode())
    updater.atomic_write(RESEARCH, (json.dumps(evidence, ensure_ascii=False, indent=2) + "\n").encode())

    videos = json.loads((DATA / "videos.json").read_text("utf-8"))
    old_ids = {v["id"] for v in videos}
    by_id = {v["id"]: v for v in evidence["videos"]}
    imported = []
    for ident, published, language, topics, title, description in ARCHIVE:
        if ident in old_ids:
            continue
        record = by_id[ident]
        embed = record["oembed"]
        parser = TextParser()
        parser.feed(embed["html"])
        assert embed["type"] == "video" and any(identity(url) and identity(url)[:2] == ("youtube", ident) for url in parser.embeds)
        assert embed["author_url"].startswith("https://www.youtube.com/")
        assert embed["thumbnail_url"].startswith("https://i.ytimg.com/")
        source = next((s for s in config["sources"] if embed["author_url"] in s["authorUrls"]), None)
        cached = next((p for p in (ROOT / "tights-guide/assets/videos-new").glob(ident + ".*") if p.suffix in {".jpg", ".png", ".webp"}), None)
        try:
            raw = cached.read_bytes() if cached else fetch(embed["thumbnail_url"], limit=8_000_000)
        except OSError:
            print("Thumbnail temporarily unavailable:", ident)
            continue
        thumbnail = "assets/videos-new/" + ident + updater.image_extension(raw)
        updater.atomic_write(ROOT / "tights-guide" / thumbnail, raw)
        item = dict(id=ident, provider="youtube", title=title, originalTitle=plain(embed["title"], 200),
                    description=description, topics=topics, language=language, kind="Архив · " + ("Звуки ткани" if "asmr" in topics else "Авторское видео"),
                    author=plain(embed["author_name"], 100), authorUrl=embed["author_url"], url=record["url"],
                    thumbnail=thumbnail, thumbnailSource=embed["thumbnail_url"],
                    thumbnailWidth=embed["thumbnail_width"], thumbnailHeight=embed["thumbnail_height"],
                    archive=True, addedBy="curated", checked=now.date().isoformat(),
                    embedCheckedAt=stamp(now), embedStatus="oembed", sourceUrl=record["url"],
                    dateStatus="verified" if published else "unconfirmed")
        if source:
            item["sourceId"] = source["id"]
        if published:
            item.update(publishedAt=published, dateSource="youtube:atom.published" if "T" in published else "youtube:public-index.published (date only)", dateVerificationUrl=record["url"])
        imported.append(item)
        videos.append(item)
    updater.validate_catalog(videos)
    updater.atomic_write(DATA / "videos.json", (json.dumps(videos, ensure_ascii=False, indent=2) + "\n").encode())
    print("Sources:", len(config["sources"]), "archive added:", len(imported), "dated:", sum("publishedAt" in v for v in imported), "undated:", sum("publishedAt" not in v for v in imported))


if __name__ == "__main__":
    main()
