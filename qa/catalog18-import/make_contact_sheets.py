"""Create review contact sheets from already-local catalogue photographs.

This does not classify a model photo as packaging. The index only maps cells to
source records; actual packaging candidates require separate visual review.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import textwrap

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("catalog18", ROOT / "scripts/collect-catalog18.py")
catalog = importlib.util.module_from_spec(spec)
spec.loader.exec_module(catalog)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=ROOT / "tights-guide/data/catalog.json")
    parser.add_argument("--brand", action="append", default=[])
    parser.add_argument("--overview", action="store_true", help="First three photographed models per brand")
    parser.add_argument("--out", type=Path, default=Path(__file__).parent / "contact-sheets")
    args = parser.parse_args()
    Image, ImageOps = catalog.pillow_runtime()
    from PIL import ImageDraw, ImageFont
    font_path = next((path for path in (Path("C:/Windows/Fonts/arial.ttf"), Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")) if path.exists()), None)
    font = ImageFont.truetype(str(font_path), 13) if font_path else ImageFont.load_default()
    rows = json.loads(args.catalog.read_text("utf-8"))["items"]
    rows = [row for row in rows if row.get("image") and (not args.brand or row["brand"].casefold() in {brand.casefold() for brand in args.brand})]
    rows.sort(key=lambda row: (row["brand"].casefold(), row["model"].casefold()))
    if args.overview:
        seen, selection = {}, []
        for row in rows:
            seen[row["brand"]] = seen.get(row["brand"], 0) + 1
            if seen[row["brand"]] <= 3:
                selection.append(row)
        rows = selection
    args.out.mkdir(parents=True, exist_ok=True)
    columns, per_sheet, cell_width, cell_height = 6, 36, 190, 270
    pages = []
    for start in range(0, len(rows), per_sheet):
        selection = rows[start:start + per_sheet]
        sheet = Image.new("RGB", (columns * cell_width, ((len(selection) + columns - 1) // columns) * cell_height), "#eeeeeb")
        draw = ImageDraw.Draw(sheet)
        index = []
        for n, row in enumerate(selection):
            x, y = (n % columns) * cell_width, (n // columns) * cell_height
            with Image.open(ROOT / "tights-guide" / row["image"]) as image:
                image = ImageOps.exif_transpose(image).convert("RGB")
                image.thumbnail((cell_width - 14, 208))
                sheet.paste(image, (x + (cell_width - image.width) // 2, y + 6 + (208 - image.height) // 2))
            lines = [f"{n+1:02d} · {row['brand']}", *textwrap.wrap(row["model"], width=25)[:2], row["id"]]
            draw.multiline_text((x + 6, y + 217), "\n".join(lines), fill="#202020", font=font, spacing=1)
            index.append({"cell": n + 1, "id": row["id"], "brand": row["brand"], "model": row["model"], "image": row["image"], "source": row["source"], "imageSource": row["imageSource"], "reviewStatus": "unreviewed-product-photo"})
        filename = f"catalog18-{'overview-' if args.overview else ''}{start//per_sheet+1:03d}.jpg"
        sheet.save(args.out / filename, quality=90)
        pages.append({"sheet": filename, "items": index})
    catalog.atomic_json(args.out / "index.json", {"reviewedAsPackaging": False, "photographs": len(rows), "pages": pages})
    print(f"Created {len(pages)} contact sheets for {len(rows)} product photographs")


if __name__ == "__main__":
    main()
