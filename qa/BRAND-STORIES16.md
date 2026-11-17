# Истории и фотографии брендов — проверка 16

Дата проверки источников и визуального отбора: **17 ноября 2026 года**.

Подготовлено **29 коротких историй** и **26 фотографий**. В финальный согласованный набор входят 25 прежних марок и четыре новые: Knittex, Marilyn, Mona, Veneziana. Annes и DANNI не включены: packaging16 не подтвердил их добавление в выпуск.

У каждого текста есть источники; длина — 37–65 слов. В production-манифесте нет выдуманных дат или основателей. Поля country/founded пропущены там, где первичных подтверждений недостаточно. История компании, появление марки и последующее приобретение различены.

Из 26 снимков 11 добавлены локально в `tights-guide/assets/brand-stories/`, остальные переиспользуют проверенные активы сайта. Новые файлы — WebP без увеличения исходного разрешения: десять кадров имеют длинную сторону 800–1200 px, Mona Cursor 60 сохранён в доступном исходном размере 500 × 720 px. Отдельные миниатюры — до 480 px по длинной стороне. Для каждого сохранены точная страница публикации, URL исходной картинки, правообладатель/публикатор, реальные размеры и подпись. Свободная лицензия не заявлена.

Все выбранные кадры просмотрены глазами: это фирменные/каталожные колготки соответствующей марки, целые образы или детали ног. Никаких сгенерированных изображений, чужих общих мужчин и фотографий упаковки вместо модного кадра. Водяные знаки источников не удалялись.

## Проверка данных

`C:\Python313\python.exe qa/brand-stories16/validate.py` — без ошибок. Проверены обязательные поля, уникальность брендов и фото, ссылки на существующие slug, длина текстов, наличие файлов, фактические размеры WebP, размеры миниатюр и охват брендов текущего архива.

В последнем запуске проверено 810 упаковок / 29 брендов; пропущенных брендов архива: 0.

## Явные исключения без фотографии

| Марка | Что проверено | Решение |
| --- | --- | --- |
| Elledue | Double Header Christy 20 и Italian Trade Agency: найдены вкладыши/упаковки, подходящий отдельный кадр не подтверждён. | `photo: null`; только краткая история. |
| Giulietta | Карточки украинской розницы и архив Charm: подтверждены изделия и производитель, изображения — упаковки. | `photo: null`. Giulia не подставлена вместо Giulietta. |
| ORO | Intimo 91997, обе галерейные картинки, и Колготки ОПТ Activity: визуально это вкладыши. | `photo: null`. Oroblù/OroDoro не подставлены. |

Glamour сначала оставался исключением из-за недоступности галереи. Финально добавлен реальный кадр Tiamo 20 из Lamoda, найденный root и повторно просмотренный мной; карточка, артикул MP002XW1PHVQ и точный imageSource сохранены. Sisi закрыт официальным кадром Video Collection на sisi.com после недоступности goldenladycompany.com и sisi.ru для загрузки.

## Источники и границы утверждений

| Бренд | Проверенная основа и редакторское решение | Источники истории |
| --- | --- | --- |
| Conte | 1997 — начало компании «Конте Спа», Гродно; не добавлен неподтверждённый отдельный запуск Conte Elegant в 2001 году. | [Conte — о компании](https://conteshop.ru/aboutus) |
| Elledue | Профиль Italian Trade Agency связывает L’Elledue с итальянским производителем из Кастель-Гоффредо. Даты Levante/LVT не перенесены на Elledue. | [Italian Trade Agency — Levante / L’Elledue](https://www.ice.it/en/my-home/find-your-italian-partner/company-details/445853/LEVANTE-L%27ELLEDUE-PRIVATE-LABEL) · [Double Header — Elledue Christy 20](https://doubleheaderusa.com/elledue-womens-christy-20-pantyhose/) |
| FALKE | 1895 — мастерская Франца Фальке-Роэна в Шмалленберге; официальный исторический раздел. | [FALKE — история компании](https://www.falke.com/uk_en/about-us/history/) |
| Filodoro | 2003 обозначает приобретение Filodoro Calze, а не основание Filodoro. Поле founded отсутствует. | [Golden Lady Company — Filodoro](https://www.goldenladycompany.com/en/brand/filodoro) · [Golden Lady Company — история](https://www.goldenladycompany.com/en/companys-history) |
| Fiore | 1998 — начало компании; 2004 — окрашивание/отделка, 2006 — узорчатые коллекции, по собственной хронологии. | [Fiore — о компании и этапах развития](https://fiore.pl/pl/content/o-nas.html) |
| Gabriella | 1996 и семейная компания в Лодзи — официальная страница O nas. Фото Arctic Second Skin имеет отдельную карточку модели. | [Gabriella — о компании](https://www.gabriella.pl/pages/o-nas) · [Gabriella — Arctic Second Skin](https://www.gabriella.pl/products/rajstopy-arctic-second-skin) |
| Gatta | 1993 относится к компании Ferax; 2004 — развитие бесшовного белья и розницы. Отдельное founded марки не подставлено. | [Gatta — о компании](https://gatta.pl/pages/about-us) |
| Giulia | Украинское производство и Новомосковская трикотажная фабрика — официальные страницы; неизвестный точный год исключён. | [Giulia — о производителе](https://giulia.com.ua/about-us) · [Giulia Hosiery — about us](https://giuliahosiery.com/about-us) |
| Giulietta | Производитель и происхождение по карточкам EVA/Novus. Это сведения розницы; даты и основатели не придуманы. | [EVA — марка Giulietta](https://eva.ua/ua/brnd-84051/) · [Novus — Giulietta, производитель и страна](https://novus.zakaz.ua/ru/products/kolgoti-dzhuleta--04820040063331/) |
| Glamour | Ассортимент и связь с Incanto Fashion Group атрибутированы поставщику; прежняя связь с Pompea не выдана за текущую. Страна и год не заданы. | [Prokolgotki — каталог Glamour](https://prokolgotki.ru/list/all/brand%3Dglamour) · [Колготки-Онлайн — Glamour Betulla 40](https://kolgotki-online.ru/product/zhenskie-kolgotki-betulla-40-glamour) · [Lamoda — Glamour Tiamo 20 DEN nero](https://www.lamoda.ru/p/mp002xw1phvq/clothes-91amour-kolgotki/) |
| Golden Lady | 1966 — начало в Кастильоне-делле-Стивьере; корпоративная хронология подтверждает приобретения Sisi и OMSA. | [Golden Lady Company — история](https://www.goldenladycompany.com/en/companys-history) · [Golden Lady Company — марка Golden Lady](https://www.goldenladycompany.com/en/brand/golden-lady) |
| Incanto | Официальный рассказ: середина 1990-х, Дезенцано-дель-Гарда; точный год не выведен из приблизительного периода. | [Incanto — история компании](https://incanto.eu/forbuyers/o-kompanii/) · [Incanto — каталог колготок](https://incanto.eu/catalog/kolgotki_i_noski/kolgotki_chulki/) |
| Innamore | Формулировка «представляет себя как итальянскую марку» атрибутирована официальному сайту. Поле country опущено; страна выпуска не приравнена к позиционированию. | [Innamore — официальный сайт марки](https://www.innamore.com/?lang=ru) · [Lamoda — Innamore Body Slim 40](https://www.lamoda.kz/p/mp002xw16ap0/clothes-innamore-kolgotki/) |
| Le Bourget | 1924 подтверждается страницей бренда, столетие — официальной публикацией о выставке Maison du Textile. | [Le Bourget — выставка к столетию](https://www.lebourget.com/pages/exposition-100-ans-le-bourget-paris) · [Le Bourget — история специализации с 1924 года](https://www.lebourget.com/collections/tops) · [Le Bourget — фантазийные колготки](https://www.lebourget.com/collections/collants-fantaisie) |
| Levante | 1960 — историческая дата Levante в Italian Trade Agency; регистрация LVT в 2013 году не принята за основание марки. Итальянское происхождение отделено от австралийского магазина. | [Italian Trade Agency — Levante / L’Elledue](https://www.ice.it/en/my-home/find-your-italian-partner/company-details/445853/LEVANTE-L%27ELLEDUE-PRIVATE-LABEL) · [Myer — Levante Suede Matte 50](https://www.myer.com.au/p/levante-50d-suede-matte-tight-in-blue) |
| Minimi | Проверен актуальный официальный адрес minimicalze.com, на который переадресует minimi.ru. Только специализация и заявленная идея марки, без догадок о стране и дате. | [MiNiMi — о бренде](https://minimicalze.com/about/) · [MiNiMi — официальный каталог](https://minimicalze.com/) |
| OMSA | 1942 — история марки, 1992 — вхождение в группу; это разные события. | [Golden Lady Company — OMSA](https://www.goldenladycompany.com/en/brand/omsa) · [Golden Lady Company — история](https://www.goldenladycompany.com/en/companys-history) |
| ORO | Самостоятельное обозначение на архивной упаковке, не Oroblù/OroDoro/модель Oro. Итальянское позиционирование атрибутировано продавцам; country и founded опущены. | [Intimo — каталог колготок ORO](https://www.intimo.com.ua/ua/zhinochi-kolhotky/oro1/) · [Inbra — марка ORO](https://inbra.shop/uk/oro) · [Колготки ОПТ — ORO Activity 40](https://kolgotkiopt.com.ua/zhenskie-kolgotki/korrektiruyushchie-kolgotki/activity-40/) |
| Omero | 1988 — запуск Filodoro Calze, март 2003 — переход к P.L.U.S.; оба события на официальной странице About. | [Omero — официальная история](https://www.omerocollant.com/en/about/) · [Omero — Retina](https://www.omerocollant.com/en/product/retina/) |
| Oroblù | 1987 — запуск марки CSP International, 1994 — Shock Up; официальный раздел Storia. | [Oroblù — история марки](https://oroblu.com/en-us/pages/storia) |
| Philippe Matignon | Приобретение вместе с Filodoro Calze в 2003 году не названо основанием. Поле founded отсутствует. | [Golden Lady Company — история приобретения Filodoro и Philippe Matignon](https://www.goldenladycompany.com/en/companys-history) · [Philippe Matignon — официальный каталог](https://www.philippematignon.it/) |
| Sisi | Официальная страница Golden Lady относит историю марки к 1925 году; корпоративная хронология фиксирует приобретение в 1987-м. Дата 1818 предшественника не использована. | [Golden Lady Company — история и специализация Sisi](https://www.goldenladycompany.com/en/brand/sisi) · [Golden Lady Company — история](https://www.goldenladycompany.com/en/companys-history) |
| Swedish Stockings | 2013, Линн Фризингер и Надя Форсберг — официальная история. Экологические заявления не обобщены на весь ассортимент. | [Swedish Stockings — история и подход к производству](https://swedishstockings.com/pages/about-us) |
| Trasparenze | 1985 — Nuova Virgiliana, 1992 — марка по хронологии производителя. Компания и марка различены; случайные юбилейные публикации с другими датами не использованы. | [Trasparenze — производство и официальная хронология](https://www.calzetrasparenze.com/produzione-calze-e-collant) |
| Wolford | 1949 — Wolff & Co., 1950 — регистрация Wolford; founded относится к марке. Корпоративный PDF и официальный исторический раздел. | [Wolford — история марки](https://www.wolford.com/en-gb/our-history.html) · [Wolford — корпоративный профиль](https://company.wolford.com/wp-content/uploads/IR/WolfordCompanyProfile.pdf) |
| Knittex | 1982 — Knittex, 2011 — запуск NOQ; название производителя сохранено. Поэтому фирменный кадр NOQ by Knittex соответствует истории Knittex. | [Knittex — о компании](https://knittex.pl/en/about/) · [Knittex — появление марки NOQ](https://knittex.pl/en/noq-brand/) · [NOQ by Knittex — Secret](https://noq.com.pl/produkt/rajstopy-damskie-secret-z-delikatnym-wzorem-kwiatow/) |
| Marilyn | 1992 и производство в Лодзи — официальная страница O nas. Gucci G46 — имя модели Marilyn, не атрибуция бренду Gucci. | [Marilyn — о компании](https://e-marilyn.pl/strony/o-nas) |
| Mona | Производитель Tespol и адрес в Константынуве-Лодзинском указаны в товарной карточке. Неофициальная дата Tespol не перенесена на марку. | [NBielizna — Mona, сведения о производителе Tespol](https://nbielizna.pl/1000202008-mona-rajstopy-mona-lucia-100-pl) · [NBielizna — Mona Cursor 60](https://nbielizna.pl/1000079784-mona-rajstopy-mona-cursor-60) |
| Veneziana | Официальный сайт подтверждает ассортимент. Непроверенные даты, владельцы и страна в метаданные не добавлены; veneziana.shop не использован. | [Veneziana — официальный каталог марки](https://veneziana.pl/) · [NBielizna — Veneziana Day 20](https://nbielizna.pl/222937-rajstopy-veneziana-day-20-den-2-4) · [NBielizna — Veneziana Satin 40](https://nbielizna.pl/1000111432-rajstopy-veneziana-satin-40-den) |

## Выбранные фотографии

| Бренд | Снимок | Размер | Публикация |
| --- | --- | --- |
| Conte | Conte · Active Soft 20. Каталожная фотография. | 1200 × 1600 | [Conte / Колготки-Онлайн](https://kolgotki-online.ru/product/zhenskie-kolgotki-active-soft-20-conte) |
| FALKE | FALKE · Matt Deluxe 20. Каталожная фотография. | 610 × 732 | [FALKE / FALKE · официальный каталог](https://www.falke.com/us_en/p/matt-deluxe-20-den-women-tights/40620_3009/) |
| Filodoro | Filodoro · Clio 50. Каталожная фотография. | 923 × 1200 | [Filodoro / G Lingerie](https://www.glingerie.com.tr/collections/opak-kulotlu-corap) |
| Fiore | Fiore · Paula 40. Каталожная фотография. | 1200 × 1600 | [Fiore / Fiore · официальный каталог](https://fiore.pl/en/womens-tights/paula-40-den.html) |
| Gabriella | Gabriella · Arctic Second Skin. Фирменная съёмка. | 960 × 640 | [Gabriella](https://www.gabriella.pl/products/rajstopy-arctic-second-skin) |
| Gatta | Gatta · Laura 20. Каталожная фотография. | 500 × 700 | [Gatta / UK Tights](https://www.uktights.com/product/11417/gatta-laura-20-den-tights) |
| Giulia | Giulia · BIKINI 20 (Smart Box). Каталожная фотография. | 504 × 700 | [Giulia / КолготкиОпт](https://kolgotkiopt.com.ua/zhenskie-kolgotki/klassicheskie-kolgotki/bikini-20-smart-box-/) |
| Glamour | Glamour · Tiamo 20. Каталожная фотография. | 600 × 866 | [Glamour / Lamoda](https://www.lamoda.ru/p/mp002xw1phvq/clothes-91amour-kolgotki/) |
| Golden Lady | Golden Lady · фирменный каталожный образ. | 960 × 864 | [Golden Lady Company](https://www.goldenladycompany.com/en/brand/golden-lady) |
| Incanto | Incanto · FASHCOL056, 40 DEN. Фирменная съёмка. | 942 × 1200 | [Incanto](https://incanto.eu/products/kolgotki_s_risunkom_v_goroshek_fashcol056/) |
| Innamore | Innamore · Body Slim 40. Каталожная фотография. | 600 × 866 | [Innamore / Lamoda](https://www.lamoda.kz/p/mp002xw16ap0/clothes-innamore-kolgotki/) |
| Le Bourget | Le Bourget · 1EF2 Chaud 100 Super Opaque Interieur Polaire. Каталожная фотография. | 900 × 1200 | [Le Bourget / Колготки-Онлайн](https://kolgotki-online.ru/product/kolgotki-art-1ef2-chaud-100-super-opaque-interieur-polaire-le-bourget) |
| Levante | Levante · Suede Matte 50, Navy. Каталожная фотография. | 720 × 928 | [Levante / Myer](https://www.myer.com.au/p/levante-50d-suede-matte-tight-in-blue) |
| Minimi | MiNiMi · La Luna 20. Каталожная фотография. | 744 × 992 | [MiNiMi / 40 DEN](https://40den.ru/zhenschinam/kolgotki/fantaziynye/minimi-la-luna-20-sredniy-goroh-daino/) |
| OMSA | OMSA · фирменный каталожный образ. | 960 × 864 | [Golden Lady Company](https://www.goldenladycompany.com/en/brand/omsa) |
| Omero | Omero · Retina. Фирменная съёмка. | 730 × 1200 | [Omero](https://www.omerocollant.com/en/product/retina/) |
| Oroblù | Oroblù · All Colors 120. Каталожная фотография. | 750 × 1000 | [Oroblù / Колготки-Онлайн](https://kolgotki-online.ru/product/kolgotki-all-colors-120-oroblu) |
| Philippe Matignon | Philippe Matignon · коллекция Collant velati. | 960 × 993 | [Philippe Matignon](https://www.philippematignon.it/) |
| Sisi | Sisi · фирменный образ из раздела Video Collection. | 874 × 1200 | [Sisi / Golden Lady Company](https://www.sisi.com/en/) |
| Swedish Stockings | Swedish Stockings · Diana Ribbed Wool Tights. | 960 × 540 | [Swedish Stockings](https://swedishstockings.com/pages/about-us) |
| Trasparenze | Trasparenze · Alison 100 Lana Merinos. Каталожная фотография. | 500 × 700 | [Trasparenze / UK Tights](https://www.uktights.com/product/2690/trasparenze-alison-tights) |
| Wolford | Wolford · Individual 20. Каталожная фотография. | 500 × 667 | [Wolford / Wolford · официальный каталог](https://us.wolford.com/en-us/individual-20-tights-18267.3265.S.html) |
| Knittex | NOQ by Knittex · Secret. Фирменная съёмка. | 960 × 1440 | [NOQ by Knittex](https://noq.com.pl/produkt/rajstopy-damskie-secret-z-delikatnym-wzorem-kwiatow/) |
| Marilyn | Marilyn · Gucci G46. Каталожный образ. | 565 × 800 | [Marilyn / NBielizna](https://nbielizna.pl/1000430160-marilyn-rajstopy-marilyn-gucci-g46-pl) |
| Mona | Mona · Cursor 60. Каталожный образ. | 500 × 720 | [Mona / NBielizna](https://nbielizna.pl/1000079784-mona-rajstopy-mona-cursor-60) |
| Veneziana | Veneziana · Satin 40. Каталожный образ. | 598 × 800 | [Veneziana / NBielizna](https://nbielizna.pl/1000111432-rajstopy-veneziana-satin-40-den) |

## Доказательства отбора

- `brand-stories16/selected-1.jpg`–`selected-3.jpg` — итоговые контактные листы всех выбранных фотографий.
- `brand-stories16/selected-photo-evidence.json` — точные URL, источник повторного использования или локальный кандидат, размеры и SHA-256 исходного локального файла.
- `brand-stories16/photos-*-result.json` — результаты получения сетевых кандидатов, включая исходные размеры/хеши, конечный URL и ошибки.
- `brand-stories16/pages-*-result.json`, `pages/*.html` — доступные исходные страницы и галереи. Ошибки загрузки отмечены отдельно и не трактуются как проверка содержимого.
- `brand-stories16/verification.json` — результаты проверок всего production-манифеста.

Отклонены после просмотра: Levante Classic Fishnet от David Jones (оказался вкладышем), изображения Levante из Italian Trade Agency (упаковки), Incanto Autumn New (гольфы, а не колготки), Annes banner s5 (повязки на бёдра). Для MiNiMi не использованы имеющиеся открытые модели Adriana/Azalea. У Veneziana выбран Satin 40 с полноценным образом вместо первоначального кадра Day 20; подпись и источник соответствуют финальному файлу.

Сетевые загрузки не отключали проверку сертификатов TLS. Отдельная попытка получить публичное изображение Sisi по HTTP завершилась без результата и не используется. Никаких внешних публикаций, аккаунтов, API-генерации или покупок не было.

Справочник `brands.js`, фотокаталог `photos.js` и существующие исходные медиа не изменялись. UI и сборку проверяет root отдельно.
