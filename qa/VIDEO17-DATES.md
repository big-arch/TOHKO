# Проверка недостающих дат · видео 17

17 ноября 2026 года. Рассмотрены 23 существующие записи без `publishedAt`: 16 YouTube, 5 Vimeo и 2 Snag. Для 21 записи YouTube/Vimeo отправлены запросы публичных метаданных; у двух Snag исходных сведений о дате нет. Видеопотоки, видеофайлы и ИИ не использовались.

## Итог

Исходные даты публичной публикации дополнительно не подтверждены. `videos.json` не изменён: у 23 роликов остаётся явная надпись о неподтверждённой дате. Vimeo вернул даты первоначальной загрузки этих конкретных видео; их нельзя без дополнительных сведений считать датами первого публичного релиза.

## Vimeo: полученные исходные поля

У всех пяти oEmbed-ответов HTTP 200; `video_id`, название и `author_name = Swedish Stockings` совпали с существующей записью. Официальная HTML-страница также вернула HTTP 200 и соответствующее название, но `datePublished`, `release_time`, `dateCreated` и JSON-LD с датой отсутствовали. Неоднозначная дата не перенесена в `publishedAt`. В `upload_date` часовой пояс отсутствует.

| ID | Поле исходного ответа | Точное значение | Evidence URL |
|---|---|---|---|
| `vimeo-1100274499` | `upload_date` | `2025-07-10 07:36:24` | [Vimeo oEmbed](https://vimeo.com/api/oembed.json?url=https%3A%2F%2Fvimeo.com%2F1100274499) |
| `vimeo-1102160026` | `upload_date` | `2025-07-17 07:11:53` | [Vimeo oEmbed](https://vimeo.com/api/oembed.json?url=https%3A%2F%2Fvimeo.com%2F1102160026) |
| `vimeo-1104089394` | `upload_date` | `2025-07-24 07:09:31` | [Vimeo oEmbed](https://vimeo.com/api/oembed.json?url=https%3A%2F%2Fvimeo.com%2F1104089394) |
| `vimeo-1225879573` | `upload_date` | `2026-09-11 04:49:33` | [Vimeo oEmbed](https://vimeo.com/api/oembed.json?url=https%3A%2F%2Fvimeo.com%2F1225879573) |
| `vimeo-1241278134` | `upload_date` | `2026-10-30 08:40:03` | [Vimeo oEmbed](https://vimeo.com/api/oembed.json?url=https%3A%2F%2Fvimeo.com%2F1241278134) |

Дополнительная сверка HTML: [vimeo-1100274499](https://vimeo.com/1100274499), [vimeo-1102160026](https://vimeo.com/1102160026), [vimeo-1104089394](https://vimeo.com/1104089394), [vimeo-1225879573](https://vimeo.com/1225879573), [vimeo-1241278134](https://vimeo.com/1241278134).

## YouTube: метаданные недоступны

У 14 страниц получен HTTP 429; у двух — TLS EOF до получения метаданных. Повторных запросов к ограничившему частоту YouTube не выполнялось. Две дополнительные поисковые проверки точных ID по домену youtube.com вернули пустой результат; опубликованные числа и относительные сроки не подставлялись.

| ID | Результат | Evidence URL |
|---|---|---|
| `8ruf9D3Cu4c` | HTTP 429; дата не получена | [Страница видео](https://www.youtube.com/watch?v=8ruf9D3Cu4c&hl=en) |
| `I85twyDA_-g` | HTTP 429; дата не получена | [Страница видео](https://www.youtube.com/watch?v=I85twyDA_-g&hl=en) |
| `LdfM-MckAf4` | HTTP 429; дата не получена | [Страница видео](https://www.youtube.com/watch?v=LdfM-MckAf4&hl=en) |
| `QpApOq2Q0l8` | HTTP 429; дата не получена | [Страница видео](https://www.youtube.com/watch?v=QpApOq2Q0l8&hl=en) |
| `d2aX0wwfPJM` | HTTP 429; дата не получена | [Страница видео](https://www.youtube.com/watch?v=d2aX0wwfPJM&hl=en) |
| `efrrmzoIA2E` | TLS EOF; дата не получена | [Страница видео](https://www.youtube.com/watch?v=efrrmzoIA2E&hl=en) |
| `eqnpEWFyvHY` | HTTP 429; дата не получена | [Страница видео](https://www.youtube.com/watch?v=eqnpEWFyvHY&hl=en) |
| `fW5YzXtsF-A` | HTTP 429; дата не получена | [Страница видео](https://www.youtube.com/watch?v=fW5YzXtsF-A&hl=en) |
| `gkbMiMVNwyg` | HTTP 429; дата не получена | [Страница видео](https://www.youtube.com/watch?v=gkbMiMVNwyg&hl=en) |
| `pHSBU0U3940` | HTTP 429; дата не получена | [Страница видео](https://www.youtube.com/watch?v=pHSBU0U3940&hl=en) |
| `s5RVt62Scgc` | HTTP 429; дата не получена | [Страница видео](https://www.youtube.com/watch?v=s5RVt62Scgc&hl=en) |
| `tSa26mVW5gM` | TLS EOF; дата не получена | [Страница видео](https://www.youtube.com/watch?v=tSa26mVW5gM&hl=en) |
| `vbIbX589Idc` | HTTP 429; дата не получена | [Страница видео](https://www.youtube.com/watch?v=vbIbX589Idc&hl=en) |
| `xws7aTD4kPU` | HTTP 429; дата не получена | [Страница видео](https://www.youtube.com/watch?v=xws7aTD4kPU&hl=en) |
| `yqTK5Gs0qmA` | HTTP 429; дата не получена | [Страница видео](https://www.youtube.com/watch?v=yqTK5Gs0qmA&hl=en) |
| `zu8UTjg3E4U` | HTTP 429; дата не получена | [Страница видео](https://www.youtube.com/watch?v=zu8UTjg3E4U&hl=en) |

## Snag

Для `snag-motion` и `snag-details` подтверждённой даты исходной публикации нет. Время создания/изменения страницы магазина, параметры CDN, числа в URL и идентификаторах не трактовались как даты роликов.

## Лимиты и способ проверки

Всего 30 внешних обращений: 21 запрос watch/oEmbed, 5 официальных HTML-страниц Vimeo, 2 попытки открыть Vimeo через web и 2 поисковых запроса. До этого 21 попытка в sandbox была остановлена локальной ошибкой сокета WinError 10013 до установления соединения; тот же read-only пакет затем выполнен с разрешением на сеть. Все обращения были чтением публичных метаданных без ключей. Ограничение времени 6 минут соблюдено.

## Сохранность локальной даты при обновлении

`scripts/update-videos.py`, функция `restore_previous`: локальный seed целиком имеет приоритет над deployed-записью с тем же ID; из live добавляются только отсутствующие локально ID. `scripts/video_feed.py`, `collect`: существующие ID не проверяются заново и не заменяются кандидатами. Новые подтверждённые локальные `publishedAt`, `dateSource` и URL доказательства не будут затёрты более старым снимком.

Выполнена отдельная offline-проверка `restore_previous` на копии полного каталога: в локальной копии заданы пробные поля даты и происхождения, в deployed-копии их нет. Возвращена полная локальная запись с точным сохранением всех трёх полей и прежним количеством видео. Исходные файлы при этой проверке не менялись. Правка merge не требуется.

UI и билдер остаются frozen. Поскольку исходный каталог не менялся, повторная сборка не нужна.
