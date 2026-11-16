# Новости ТОНКО — 16 ноября 2026

Исходное состояние: 40 записей, из них 28 содержали только заголовок или короткий RSS-анонс. Итог: 40 готовых статей, 40 локальных изображений, 0 pending, 0 failed в текущем снимке. Подготовлены 28 самостоятельных русских пересказов и 28 недостающих изображений; зимняя статья и её фотография переработаны отдельно. Оплачиваемый API локально не вызывался.

## Причины и изменения

- Google News раньше исключался из enrich по полю via, но получал ту же кнопку чтения. Теперь первоисточник разрешается только внутри allowlist: сохранённый publisherUrl, совпадение заголовка в RSS издателя, поиск RSS Bracatus и ограниченный редирект Google.
- Порог 220 слов отбрасывал полноценные короткие анонсы Swedish Stockings на 170–215 слов. Новый минимум источника — 140, короткий пересказ допустим при достаточном фактическом содержании.
- Одна проверка готовности используется Python-сборкой и воспроизведена в клиентской ленте: вступление, разделы и не менее 65 слов основного текста. Заголовки без тела не публикуются как статьи.
- В news.json сохранены все открытия и publication.status/reason/checkedAt/nextAttemptAt/attempts/fetchAttempts; очередь видна в блоке «Как обновляется лента». Приватный cache дублируется безопасными счётчиками в публичном снимке.
- Неудачи источника повторяются через 30 минут, 6 часов, сутки, затем неделю. Невалидный текст не оплачивается бесконечно: максимум 3 попытки на неизменившийся исходник, затем проверка изменений.
- Бюджет: 6 запросов за запуск, 60 в сутки, 2200 выходных токенов на запрос, 18000 символов входного текста. Через 6 минут новые задачи в партии не начинаются; расписание — каждые 15 минут.
- Архив имеет отдельный лимит 200 готовых статей; ещё до 200 открытий хранятся в очереди. Новые необработанные заголовки не могут вытеснить готовую статью. Готовые статьи не исчезают автоматически через год. Главная раскрывает по 6; статическая news.html содержит весь готовый архив. После 200 готовых публикаций старейшие выходят из архива — это преднамеренный предел текущего снимка.
- Восстановлен независимый от AI-ключа backfill_covers с лимитом 6 проверок за запуск. Для API-попыток отдельно хранятся paidStatus/paidAt: временный сбой первоисточника больше не блокирует недельное восстановление после трёх ошибок API.
- Сборка assistant knowledge вызвана после build-home-news; пустые материалы должен отфильтровать его publication gate.
- В CI перед генерацией и публикацией выполняются тесты новостей, видеопамяти и помощника: test_assistant.cjs, test_assistant_cache.cjs, test_assistant_build.py.

## Две исходные жалобы

- ee8ae4a2a6c7f547: заменён летний OG-коллаж на визуально проверенную фотографию @lovisabarkman: закрытое пальто, шляпа, легинсы и высокие сапоги. Подпись явно указывает другую подборку Who What Wear и отсутствие температурной гарантии. Для будущих зимних статей непроверенный OG автоматически не подставляется.
- d97ca36124a1dd82: найден https://bracatus.com/kalendar-nosochno-chulochnogo-mira, подготовлены 4 раздела. Ошибка Bracatus о пяти миллионах пар в первый день продаж исправлена по American Chemical Society: около 800 тысяч; добавлена прямая ссылка на исторический материал ACS.

## Проверки

- 57 unit-тестов новостей: PASS; включены Google-resolver, запрещённый издатель, повторные попытки, восстановление после потери cache, лимит оплаты, короткий достоверный источник, архив старше года и три регрессии из независимого ревью.
- qa/check-news-queue.py: PASS в Edge; все 40 тел, все 40 ссылок, все 40 изображений загружаются (naturalWidth > 0) и локальны, pending/failed без кнопки чтения, источник календаря, мобильная ширина 390 и desktop 1440, 0 JS ошибок.
- news.html без JavaScript: все 40 статей доступны.
- scripts/check-site.py: PASS, 35 HTML-страниц; node --check для обоих изменённых JS: PASS.
- Повторная сборка по сохранённым RSS: все 40 прежних готовых ссылок сохранены.
- Дополнительные тесты помощника, включённые в CI: 19 Node + 3 Python — PASS.

## Изображения

Все 40 статей имеют локальное изображение с подписью и ссылкой на источник. Из них 39 — реальные фотографии или фотоколлажи, 1 — явно обозначенная тематическая иллюстрация календаря Bracatus. Ни одной статьи без изображения в текущем выпуске нет.

Для 28 прежде пустых статей добавлены: 21 фотография непосредственно из обсуждаемой публикации, 1 официальная фотография конкретной модели из дайджеста, 5 явно подписанных тематических фотографий изделий и 1 иллюстрация календаря. Пять тематических кадров показывают серый ромб, винный цвет, шерстяной рубчик, розничную упаковку и конструкцию тёплых колготок; их происхождение не выдаётся за источник статистики или за иной бренд. Эти 28 WebP занимают 6,27 МБ. Единственное внешнее RSS-фото CSB также локализовано и проверено.

Реестр источников и проверки — [photo-review.json](photo-review.json). Общий контактный лист — [all-40-images.jpg](all-40-images.jpg). Зимняя статья: [мобильный экран](ee8ae4a2a6c7f547-390.png), [desktop](ee8ae4a2a6c7f547-1440.png). В будущих зимних публикациях автоматическая обложка OG без отдельной проверки не используется.

## Внешнее ограничение

Прямой HTTPS к Bracatus с текущей Windows-машины завершается ошибкой TLS до HTTP (проверены основной хост, www, RSS и robots.txt). Текущий backlog прочитан через доступные web/Firecrawl источники и полностью подготовлен. Будущие недоступные статьи будут честно ожидать повторной проверки; нельзя гарантировать доступность внешнего сайта. Настоящий платный этап и GitHub deployment проверяет родительский агент после интеграции.

## Подготовленные материалы

| ID | Статья | Первоисточник |
|---|---|---|
| fb9e23837e95c12e | Как Swedish Stockings представил новую коллекцию в Стокгольме | [Swedish Stockings](https://swedishstockings.com/blogs/journal/reimagining-hosiery-an-evening-with-swedish-stockings) |
| bfd2f03ae301d568 | Балерина Дарья Иванова в кампании Swedish Stockings AW26 | [Swedish Stockings](https://swedishstockings.com/blogs/journal/aw26-behind-the-scenes) |
| d4e8e16255104b16 | Новый логотип и упаковка Swedish Stockings: что изменилось | [Swedish Stockings](https://swedishstockings.com/blogs/journal/introducing-a-new-era) |
| ecfefa91acbb25c6 | Легинсы со штрипками: три детали образа в гиде Swedish Stockings | [Swedish Stockings](https://swedishstockings.com/blogs/journal/stir-up-leggings-style-guide) |
| 42c8582c92a885b1 | Лиссабонская съёмка Swedish Stockings: кружево, капри и летний цвет | [Swedish Stockings](https://swedishstockings.com/blogs/journal/behind-the-scenes-occasion-campaign-2026) |
| 027ada4e3cdc30c2 | Rave Rvw: как переработанные ткани встречаются с цветными колготками | [Swedish Stockings](https://swedishstockings.com/blogs/journal/rave-review-journal) |
| b8f663fe189f9015 | Весенние сочетания Swedish Stockings: от коричневого кружева до голубого | [Swedish Stockings](https://swedishstockings.com/blogs/journal/style-guide-for-spring-legwear) |
| 40f2838465682250 | August Barron × Swedish Stockings: сетка поверх трикотажа | [Swedish Stockings](https://swedishstockings.com/blogs/journal/threading-fashion-and-form-the-swedish-stockings-august-barron-collaboration) |
| 6d993c552faf7a1d | Лондон AW26: колготки и гольфы Swedish Stockings на показах | [Swedish Stockings](https://swedishstockings.com/blogs/journal/ldn-fw) |
| 456f77b8a76349b5 | Нью-Йорк AW26: цвет, кружево и рубчик на подиуме | [Swedish Stockings](https://swedishstockings.com/blogs/journal/nyfw-aw26-recap) |
| e41511467a863f74 | Копенгаген AW26: кружево, цветные колготки и высокие носки | [Swedish Stockings](https://swedishstockings.com/blogs/journal/cphfw-aw26-runway-recap) |
| 11c995bf8463959a | Контрасты в коллекции Swedish Stockings весна–лето 2026 | [Swedish Stockings](https://swedishstockings.com/blogs/journal/bts-ss26) |
| ffca86dd42910ddb | Итоги года Swedish Stockings: производство, США и вторая жизнь колготок | [Swedish Stockings](https://swedishstockings.com/blogs/journal/a-letter-from-our-founder-ceo-linn-frisinger) |
| 702f48398a3ac4d2 | От Копенгагена до Лондона: чулочный трикотаж на показах SS26 | [Swedish Stockings](https://swedishstockings.com/blogs/journal/fashion-week-ss26-recap) |
| d97ca36124a1dd82 | Календарь чулочного мира: история нейлона и неофициальные праздники | [bracatuS](https://bracatus.com/kalendar-nosochno-chulochnogo-mira) |
| b4a87c1b9cc86aa7 | Серые колготки: как меняется привычная нейтральная основа | [bracatuS](https://bracatus.com/serye-kolgotki-stanovyatsya-alternativoj-klassicheskim-chyornym) |
| e91f3ab7c1d5c5c6 | Тёплые колготки: что сравнивать кроме числа DEN | [bracatuS](https://bracatus.com/tyoplye-kolgotki-2026-entsiklopediya-materialov-tehnologij-stilnyh-kombinatsij) |
| 2df0d94c6bc34bf9 | Фактура вместо однотонности: три подхода к декоративным колготкам | [bracatuS](https://bracatus.com/kunert-philippe-matignon-trasparenze-delayut-stavku-na-fakturnye-kolgotki) |
| 2e20b7543f721dfc | Колготки и носки: разная динамика покупок за девять месяцев | [bracatuS](https://bracatus.com/kolgotki-pokupayut-chashhe-noski-rezhe-v-rossii-vyrosli-tseny-na-obe-kategorii) |
| 5fcce6d8671b2313 | Хлопок, шерсть или микрофибра: выбор колготок под свой маршрут | [bracatuS](https://bracatus.com/v-kakih-kolgotkah-ne-budet-holodno-hlopok-sherst-ili-mikrofibra) |
| 31970a45d545a6b9 | Как устроены тёплые колготки: нить, ворс и несколько слоёв | [bracatuS](https://bracatus.com/iz-chego-kak-delayut-sovremennye-tyoplye-kolgotki) |
| 965179ab4f08fa88 | Белые Omsa Groenland 250: что показал обзор и чего он не обещает | [bracatuS](https://bracatus.com/obzor-belye-kolgotki-na-mehu-omsa-groenland-250) |
| 4e85ad88e518b74a | «Спущенные» колготки Julie Kegels: подиумная игра с гравитацией | [bracatuS](https://bracatus.com/effekt-spushhennyh-kolgotok-gravitatsiya-ironiya-dekonstruktsiya-v-kollektsii-julie-kegels-vesna-leto-2027) |
| 7c98f83e81c54f4e | Осень–зима 2026/27: цвет и фактура в подборке Bracatus | [bracatuS](https://bracatus.com/modnye-tyoplye-kolgotki-osen-zima-2026-2027) |
| 10c2e58a93d5b519 | Dvorak C57: шерстяная смесь и детали посадки в обзоре Bracatus | [bracatuS](https://bracatus.com/obzor-sherstyanye-kolgotki-dvorak-c57-utilitarnyj-sogrevayushhij-zimnij-variant-s-verblyuzhej-i-ovechej-sherstyu) |
| d04e413ae5925279 | Бордо, шоколад и графит: три спокойных способа добавить цвет | [bracatuS](https://bracatus.com/bordovyj-shokoladnyj-grafit-gid-po-modnoj-palitre-kolgotok-na-osen-zimu) |
| 401469c4e6dfb62c | От офисной обязанности к модному акценту: взгляд на историю колготок | [bracatuS](https://bracatus.com/ot-panihidy-renessansa-evolyutsiya-kolgotok-ot-nachala-2000-h-2026-go) |
| 6b27edbb1086a9a4 | Чулочная отрасль в октябре: цвет, новые материалы и давление затрат | [bracatuS](https://bracatus.com/dajdzhest-novostej-chulochno-nosochnoj-otrasli-oktyabr-2026) |
