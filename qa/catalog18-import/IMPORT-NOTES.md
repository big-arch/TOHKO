# Loretta catalogue import

The maintained entry point is `scripts/collect-catalog18.py`. The parser uses
Python's standard library. Image conversion requires Pillow. The image helper
can reuse `TONKO_PILLOW_RUNTIME` or the project's existing local Pillow runtime.

```powershell
& 'C:\Python313\python.exe' -X utf8 scripts/collect-catalog18.py --workers 4
& 'C:\Python313\python.exe' -X utf8 qa/catalog18-import/test_parser.py
```

For a clean Linux runner:

```sh
python -m pip install Pillow
python -X utf8 scripts/collect-catalog18.py --workers 4
python -X utf8 qa/catalog18-import/test_parser.py
```

## Scope and completeness

The source menu supplies 62 public subcategories: classic tights, patterned
tights, children's tights, hold-up stockings and suspender stockings. Other
underwear, socks, knee-highs and leggings categories are outside scope. Mixed
listings are classified from their source facts; unrelated leggings etc. are
listed in the exclusion report. A nylon accessory is never silently relabelled
as tights merely because it is filed under a tights category.

The source's `rel=next` links are followed. Loretta currently renders cumulative
pagination (10 cards, then 20 cards, etc.). After this is demonstrated by the
actual first two pages, the collector can read the final public page directly.
Every category must have exactly the advertised unique product count, and the
report records every fetched URL, date, count and skipped redundant page count.
A standard noncumulative listing is followed page by page.

Duplicates are merged by source SKU, internal product ID and product URL slug.
Category memberships remain attached to one product. Prices, old prices and
availability use separate source elements. Missing prices stay `null`; prices
are never inferred from product names or assigned zero. Price observations keep
the HTTP fetch timestamp even when the parser or image optimizer is rerun.

## Safe repeated operation

The HTTP cache is `qa/catalog18-import/http-cache/`. HTML expires after 24 hours;
image URLs are cached for resuming an interrupted download. Network requests use
at most four workers and a global 0.3-second interval between starts. Failures
have bounded retries; eight consecutive failed requests open a circuit breaker.
TLS certificates are verified. `--tls12` limits TLS to version 1.2 for an
incompatible local transport, without disabling verification.

`--transport curl` optionally uses the installed curl executable for both source
HTML and image requests. It keeps TLS verification, HTTPS-only redirects, the
same response-size limits, cache and retries. Bodies are written only to bounded
temporary cache files; subprocess stdout contains metadata. The default remains
Python urllib, and transport choice does not change source URLs or network
settings.

A complete snapshot less than 24 hours old skips collection. `--refresh` forces
fresh HTML. `--resume` reparses still-valid cached HTML and completes images.
`--offline` makes no network requests. `--no-images` is a data-only run and retains
existing image paths only when their source URL is unchanged.

`--deployed https://example.org/tights-guide/` restores the published JSON and
missing local catalogue WebP files before checking snapshot age. Only complete
Loretta snapshots and constrained `assets/catalog/*.webp` paths are accepted.
Restore failure does not replace existing JSON.

Exit status 3 means the deployment could not be safely restored and must stop
publication. A 404 for `data/catalog.json` is permitted only for the first
publication when a complete, valid repository seed and all its local images
exist. A missing deployed image, malformed JSON, TLS error or other restore
failure remains fatal even if an older repository snapshot is available.

An incomplete source crawl writes `catalog-candidate.json` and
`coverage-report.json` under this QA directory, returns exit code 2 and leaves
the published JSON untouched. A complete crawl atomically replaces
`tights-guide/data/catalog.json`. `packageId` associations already added to the
published catalogue are retained by stable ID.

Frequent news deployments use
`--restore-only --deployed https://example.org/tights-guide/`. This restores and
validates the complete snapshot and its local WebP containers, returns 0, and
never creates the Loretta source client. The full collection can therefore run
in a separate daily workflow without delaying news publication.

The review candidate and coverage report are also written immediately after the
listing phase, then checkpointed after every 100 image jobs. `phase`,
`imagePhaseComplete` and `published` distinguish a resumable review candidate
from the final publication. If the image phase is interrupted, collected product
facts remain available for inspection while published data stays unchanged.

Source HTML is decoded strictly using HTTP and HTML meta charset declarations,
including Windows-1251. Conflicting charsets and replacement characters stop
that category instead of silently publishing damaged Russian labels.

## Image handling and review

Published images are local WebP files, maximum 1200 pixels on the long side,
without enlargement; thumbnails have a maximum side of 320 pixels. An image
download failure leaves nullable image fields and appears in the report. Product
records describing potentially explicit accessories, bodysuits or erotic open
constructions retain their facts but their photos await review.

When a source photo URL changes, its new filename contains the URL hash. The old
photo cannot be assigned to the new URL if the replacement download fails.
Unchanged source URLs keep valid existing local image paths.

The first review CI timed out after downloading 648 image pairs before saving
its product JSON. `initial-images-manifest.json` pins their Git blobs and SHA256
checksums to run 44085884185 / commit 6fffdb4. Only the explicitly enabled
`--initial-image-manifest` review flag can bind these first-run legacy filenames
to matching SKUs and source product/image identifiers from a new listing. The
resolved evidence is saved separately; normal daily refresh never uses this
exception. This initial binding is documented as provenance reconciliation, not
as a claimed byte comparison against newly downloaded originals.

Catalogue product photos do not automatically become packaging archive entries.
Packaging must be identified visually and separately approved in the packaging
manifest. Full shop descriptions and reviews are not published: the generated
description contains only product type, documented density and explicit gender.

## Initial local transport findings

On 2026-11-17, the homepage, men's listing, its next page, the Thor detail page
and several stocking listings downloaded successfully. Subsequent local Python
and Windows curl requests intermittently failed during TLS handshake, before
receiving HTML. Strict TLS 1.2 did not resolve the local failure. Network settings
were not changed. The incomplete local crawl is not a complete published import;
a full successful run in a working environment is required.
