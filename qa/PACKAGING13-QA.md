# PACKAGING13 — проверка расширенного архива

Дата: 16 ноября 2026.

**501 → 715 карточек, 25 брендов. Добавлено 216 карточек; два старых повтора объединены.** У каждого бренда минимум 20 реальных изображений упаковок/фирменных вкладышей. Цвета, размеры и дополнительные ракурсы одного оформления не увеличивают число карточек.

**Swedish Stockings: 25 карточек — 21 упаковка колготок, 3 гольфов и 1 легинсов. Минимум 20 упаковок колготок достигнут.** Типы явно указаны в заголовках карточек, `productKind`, описании и под счётчиком группы, также без JavaScript. Старый обзорный снимок трёх новых упаковок считается одной карточкой, не тремя. Дополнительно подтверждены Tora Shimmery 20, Beata Seamless 15, Doris Dots 40, Ylva Wool Fishbone и Lo Lace 40. Комплект Beata из трёх пар считается одной карточкой; DEN Ylva не установлен и оставлен null. Белая архивная коробка Doris отличается оформлением от Doris на обзорном снимке новой линейки.

## Числа по брендам

| Бренд | Было | Стало |
|---|---:|---:|
| Conte | 75 | 75 |
| Elledue | 7 | 21 |
| FALKE | 1 | 20 |
| Filodoro | 13 | 26 |
| Fiore | 4 | 21 |
| Gabriella | 7 | 21 |
| Gatta | 5 | 26 |
| Giulia | 15 | 25 |
| Giulietta | 9 | 20 |
| Glamour | 15 | 23 |
| Golden Lady | 23 | 23 |
| Incanto | 25 | 25 |
| Innamore | 48 | 48 |
| Le Bourget | 11 | 24 |
| Levante | 32 | 32 |
| Minimi | 36 | 36 |
| OMSA | 42 | 42 |
| ORO | 1 | 20 |
| Omero | 30 | 30 |
| Oroblù | 36 | 36 |
| Philippe Matignon | 9 | 20 |
| Sisi | 21 | 21 |
| Swedish Stockings | 1 | 25 |
| Trasparenze | 34 | 34 |
| Wolford | 1 | 21 |

## Проверка подлинности и повторов

- Все новые изображения просмотрены визуально на контактных листах; спорные изображения раскрывались отдельно. Повторная проверка собранных WebP: `.cache/pack13/accepted-1.jpg` … `accepted-9.jpg`. Поиск по названию сам по себе не считался подтверждением: поисковик неоднократно возвращал другие модели или бренды.
- Использованы фирменные вкладыши, фотографии реальных коробок/пакетов, обороты упаковок и опубликованные изображения оформления. Не использованы обычные фотографии моделей без упаковочного оформления, сгенерированные изображения или повторные цвета/размеры для увеличения количества.
- Старые Gabriella Arctic 500 (`pkg-f6bee3c646` → `pkg-d10414bb40`) и Giulietta CHARM 40 NEW (`pkg-894e2ff1ef` → `pkg-7e3c594182`) объединены. Вторые фотографии и их источники сохранены в `variants`.
- Новые Gatta Julia Stretch 15: коробка и плоский вкладыш с одинаковым оформлением объединены в `pkg-8a23ab288e`; `pkg-b9e7bd3046` — дополнительное фото, не отдельная карточка.
- Старые прямые ссылки на объединённые ID открывают основную карточку. Изображения вариантов доступны локально из просмотра.
- Wolford Fatal 15 / root-020 исключён: открытый вкладыш частично закрыт вещью, точное соответствие модели недостаточно подтверждено. Обе производные WebP удалены из публикуемых assets. Wolford — 21.
- Разные модели/плотности и действительно изменившееся оформление оставлены отдельно. Например, ORO Activity 40 в старой фиолетовой и новой белой композиции, Giulietta Super 40 с разными фотографиями, Elledue Estivo 7 с разной версткой. Пометка XL сама по себе основанием для новой карточки не была.
- DEN неизвестной плотности оставлен `null`; числовые артикулы вроде FALKE 40658 и Gabriella Kabarette 151 не превращены в DEN.

## Источники и хранение

Каждая новая карточка содержит `source`, `imageSource`, `sourceName`, `checked`, `license`, локальные `image`/`thumbnail` и фактические размеры. Основные источники: брендовые каталоги КолготкиОпт; предметные карточки магазинов, Allegro и eBay; обзоры iLoveHosiery; официальный Swedish Stockings. Модель уточнялась по читаемой упаковке, когда поисковое название ей противоречило.

Примеры проверяемых источников:

- [ORO Press Up 20 — Natamoda](https://www.natamoda.com.ua/kolgoti/20-zhenskie-kolgoti-press-up-oro-20-den-telesnij): на вкладыше читается 20 DEN; это отдельная модель от Press Up 40.
- [Giulietta Super 40 — КолготкиОпт](https://kolgotkiopt.com.ua/zhenskie-kolgotki/klassicheskie-kolgotki/kolgotki-giulietta-super-40/): два разных оформления в галерее одной модели, а не два ракурса.
- [Philippe Matignon Premiere 15 vita bassa — Bianka](https://bianka.com.ua/ru/kolgoty/zhinochi-kolgoty-philippe-matignon-premiere-15-vita-bassa-italiya/): крупный фирменный вкладыш из карточки модели.
- [Swedish Stockings Lois Rip Resistant — официальный каталог](https://swedishstockings.com/products/lois-rip-resistant-tights-bundle): комплект двух пар считается одной карточкой.

216 новых основных фотографий и один дополнительный ракурс сохранены как WebP; к каждой есть thumbnail шириной не более 320 px. Изображения не дорисовывались; применены ориентация EXIF, ограничение размера и кодирование WebP. Полные исходные кадры сохранены в рабочем кэше. Свободная лицензия не заявлялась; происхождение каждого изображения записано в данных.

## Техническая проверка

- Проверены 1436 локальных файлов основных изображений, thumbnail и сохранённых вариантов: декодирование, размеры, существование файлов, уникальность ID.
- Одинаковых SHA-256 среди основных изображений нет. Это дополнительная техническая проверка, не замена визуальному сравнению.
- `packaging.json`, `packaging.js` и полный HTML без JavaScript содержат 715 одинаковых ID. Все ссылки `source` используют HTTPS.
- Edge/Playwright: PASS. Все 25 брендов, поиск, DEN, кнопка «Показать ещё», масштабирование, стрелки клавиатуры, Escape/возврат фокуса, пустой результат и прямые ссылки.
- Проверены ширины 320, 390, 768 и 1440 px; горизонтального переполнения нет. Пять последних Swedish-карточек открыты по прямым ссылкам с загрузкой полного фото. Ошибок JavaScript — 0. Все 715 карточек доступны в режиме без JavaScript.
- Дополнительная проверка: три старых/объединённых ID, локальные ссылки на ракурсы и подпись Swedish Stockings «колготки — 21, гольфы — 3, легинсы — 1».
- `scripts/build-packaging.py --packaging-only` пересобирает только страницу архива и данные. Значения 715 точечно синхронизированы в существующих блоках `pack-link` и `pack-sources` страниц lookbook, brands и sources.
- Версия ресурсов архива: `v=13`. Новостные, главная страница и assistant-файлы этой работой не изменялись.

Снимки браузера: `qa/pack13-desktop.png`, `qa/pack13-mobile.png`, `qa/pack13-swedish-mobile.png`. Результаты проверок: `.cache/pack13/structural-qa.json`, `browser-qa.json`, `focused-qa.json`.

## Новые карточки по брендам

**Elledue — 14:** POLARE DONNA (акрил) Elledue; RETINA 40 сетка Elledue; ESTIVO 7 Elledue; BODY FORM 40/150 Elledue; LE CAREZZE 40 con.top Elledue; Gold 40 · оформление с белым кубом Elledue; Large Net Elledue; Estivo 7 · оформление с горизонтальным логотипом Elledue; Support Soft 60 Elledue; Christy 15 Elledue; Support 40 Elledue; Christy 20 Elledue; Juliette 50 Elledue; Derby 20 Elledue.

**FALKE — 19:** Net 40658 FALKE; Intrigue 30 FALKE; Fashion Polka Dot FALKE; Shaping Panty 50 FALKE; Vitalize 20 FALKE; Matt Deluxe 20 FALKE; Vitalize 40 FALKE; Invisible Deluxe Shaping 8 FALKE; Invisible Deluxe 8 FALKE; Overknee 25 FALKE; Natural Glow 6 FALKE; Seidenglatt 80 FALKE; Seidenglatt 40 FALKE; Seidenglatt 15 FALKE; Lunelle 8 FALKE; Sensation 20 Seamless FALKE; Fond de Poudre 10 FALKE; Pure Shine 15 FALKE; Magic Evening 20 FALKE.

**Filodoro — 13:** SEGRETISSIMO 15 Filodoro; THERMO FEELING Filodoro; COTTON WOOL 100 Filodoro; OK SHAPE 40 control top Filodoro; PAOLA 100 Filodoro; REGINA 160 Filodoro; SEGRETISSIMO 30 Filodoro; SLIM 40 control top Filodoro; POIS Filodoro; COTTON WARM 100 Filodoro; COTTON WOOL 160 Filodoro; LINEA CHIC 20 Filodoro; REGINA 100 Filodoro.

**Fiore — 17:** Fidele 20 Fiore; First Date 20 Fiore; Mama 20 Fiore; Joie 20 Fiore; Egalite 8 Fiore; Olga 100 Fiore; Lili 20 Fiore; Julia 30 Fiore; Eccola 20 Fiore; Rewita Flow 20 Fiore; Sava 15 Fiore; Rising Love 30 Fiore; Encore 20 Fiore; Vintage · геометрический горошек, 15 DEN Fiore; Mama 40 Fiore; Thema 30 Fiore; Raffina 30 Fiore.

**Gabriella — 15:** Cacti 20 Gabriella; Microfibre 40 Gabriella; Piano 50 Gabriella; Puntina 20 Gabriella; Judie Gabriella; Kabarette 151 Gabriella; Lina 60 Gabriella; Gloria 20 · оборот упаковки Gabriella; Medica Relax 40 Gabriella; Ice Cream 20 Gabriella; Exclusive 10 Gabriella; Medica Massage 40 Gabriella; Medica Relax 20 Gabriella; Medica Push Up 40 Gabriella; Medica Push Up 20 Gabriella.

**Gatta — 21:** Touch of Cashmere Gatta; Gatta × Wedel Microfibre 40 Gatta; Funny 05 · 20 DEN Gatta; Arabesca 03 · 40 DEN Gatta; Monica 20 Gatta; Rosalia 60 Gatta; Florence 50 Gatta; Comfort Style 20 Gatta; Body Relax Medica 70 Gatta; Fortissima 15 Gatta; Rosalia 100 Gatta; Ellen 15 Gatta; Dotsy W.17 · 20 DEN Gatta; Classic Microfibre 40 · 2-pack Gatta; No Cellulite 50 Gatta; Chiara 20 Gatta; Julia Stretch 15 Gatta; Gatta × Wedel Microfibre 20 Gatta; Antistatic Effect 17 Gatta; Body Shaper 20 Gatta; Trendy Girl-Up 14 · 20/40 DEN Gatta.

**Giulia — 10:** INLAY 60 (8) Giulia; TALIA MODELLING 40 Giulia; IMPRESSO LOVE 20 Giulia; SAPPHIRE 40 Giulia; ENJOY MELANGE 60 (3) Giulia; ENJOY MELANGE 60 (2) Giulia; SPLASH 70 (4) Giulia; MIRACLE 40 (1) Giulia; ALIKE 40 (1) Giulia; MIRACLE 40 (2) Giulia.

**Giulietta — 12:** THERMO 100 Giulietta; VELOUR 70 Giulietta; VELOUR 150 Giulietta; COTONE 200 Giulietta; LANA 180 Giulietta; SUPER 40 Giulietta; ARCTIC 200 Giulietta; Lana 180 · оформление с силуэтом Giulietta; Thermo 100 · оформление с силуэтом Giulietta; Class 20 · оформление с силуэтом Giulietta; Vita Bassa 40 · оформление с чёрным бельём Giulietta; Super 40 · оформление с сиреневой блузой Giulietta.

**Glamour — 8:** GINESTRA 20 vita bassa Glamour; THIN BODY 20 vita bassa Glamour; EDELWEISS 80 vita bassa Glamour; GARDENIA 20 vita bassa Glamour; RELAX GUAINA 40 Glamour; POSITIVE PRESS 30 Glamour; GLICINE 50 vita bassa Glamour; GLICINE 20 v/bassa Glamour.

**Le Bourget — 13:** Voilance 15 Le Bourget; Voilance 15 · архивное оформление с золотым фоном Le Bourget; Couture Microfibre 15 Le Bourget; Collant effet bas · архивная синяя упаковка Le Bourget; Chaud · архивная упаковка Le Bourget; Cendrillon · архивная упаковка Le Bourget; Soyance 40 Le Bourget; Gilda 20 Le Bourget; Opaque Mat 45 · Confort 3D Le Bourget; Jambes Actives Le Bourget; Résille de Couleur Le Bourget; Eva 20 · Glamour Le Bourget; Teint Magique Sculptant 15 Le Bourget.

**ORO — 19:** ACTIVITY 40 ORO; ALASKA 120 3D ORO; STYLE 20 ORO; TOP 40 ORO; PRESS-UP 40 ORO; ARCTICA 250 ORO; EROTIC TOP 30 ORO; BIKINI 20 ORO; MICRO 100 ORO; ACTIVITY 20 ORO; NUDO 20 ORO; NUDO 40 ORO; BIKINI 40 ORO; MICRO 70 ORO; Arctica Warm Cotton 600 ORO; Arctica Hot Touch 600 Wool ORO; Activity 40 XL · оформление с белым верхом ORO; Arctica Classic Cotton 350 ORO; Press Up 20 ORO.

**Philippe Matignon — 11:** Tulle 30 Philippe Matignon; Oro 40 Philippe Matignon; Revitalise 70 Philippe Matignon; Nudite Cristal 30 Philippe Matignon; Diamants Philippe Matignon; Côte d’Azur Philippe Matignon; All Day 50 Philippe Matignon; Jade Philippe Matignon; Vernissage Philippe Matignon; Nudite Silhouette 70 Philippe Matignon; Premiere 15 vita bassa Philippe Matignon.

**Swedish Stockings — 24:** Lois Rip Resistant · комплект из двух пар Swedish Stockings; Olivia Premium 60 Swedish Stockings; Amanda Premium Maternity 20 Swedish Stockings; Maria Innovation Swedish Stockings; Lovisa Innovation 50 Swedish Stockings; Cecilia Innovation Swedish Stockings; Elin Premium 20 · упаковка и вкладыши Swedish Stockings; Edith Lace Swedish Stockings; Svea Premium 30 Swedish Stockings; Tyra Rib Leggings Swedish Stockings · легинсы; Malva Ladder Resistant 20 Swedish Stockings; Anna Control Top 40 Swedish Stockings; Liv Net Swedish Stockings; Lia Premium 100 Swedish Stockings; Viveca Stripe Swedish Stockings; Nova Lace Swedish Stockings; Bea Support Knee-Highs 60 Swedish Stockings · гольфы; Rosa Lace Knee-Highs Swedish Stockings · гольфы; Elin Premium Knee-Highs 20 · комплект из двух пар Swedish Stockings · гольфы; Tora Shimmery 20 Swedish Stockings; Beata Seamless 15 · комплект из трёх пар Swedish Stockings; Doris Dots 40 Swedish Stockings; Ylva Wool Fishbone Swedish Stockings; Lo Lace 40 Swedish Stockings.

**Wolford — 20:** Stardust 60 Wolford; Nineties Wolford; Tummy 20 Control Top Wolford; Natural Opaque 50 Wolford; Velvet Sensation Wolford; Mini Stripes Wolford; Comfort Cut 40 Wolford; Romance Net Wolford; Mira Wolford; Miss W 30 Leg Support Wolford; Emma Wolford; Sheer 15 Wolford; Madeline Wolford; Velvet de Luxe 50 Wolford; Individual 20 Wolford; Individual 10 Wolford; CNY Tiger Wolford; Velvet de Luxe 66 Wolford; Tummy 66 Control Top Wolford; Satin Opaque 50 Wolford.
