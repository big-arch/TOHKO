"""Link the price catalogue after all page builders, without touching assistant regions."""
from html import escape
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / 'tights-guide'


def main():
    catalogue = json.loads((SITE / 'data/catalog.json').read_text('utf-8'))
    items = catalogue['items']
    count, brands = len(items), len({item['brand'] for item in items})
    entry = f'''<!-- tonko-catalog --><section class="portal-container home-looks home-catalog"><div class="looks-heading"><div><p class="portal-eyebrow">Модели. Бренды. Цены.</p><h2>Найти свою пару.</h2></div><p>{count} моделей, {brands} брендов. Колготки и чулки из каталога «Лоретты»: сравните плотность, выберите ценовой диапазон и рассмотрите фотографии. Рядом с ценой в рублях — справочная сумма в долларах.</p></div><a class="experience-text-link" href="catalog.html">Каталог колготок и чулок →</a></section><!-- /tonko-catalog -->'''
    for path in SITE.glob('*.html'):
        old = path.read_text('utf-8')
        text = old
        def navigation(match):
            nav = match[0]
            if re.search(r'<a\b[^>]*href="catalog\.html"', nav):
                return nav
            link = '<a href="catalog.html"'+(' class="active" aria-current="page"' if path.name == 'catalog.html' else '')+'>Каталог</a>'
            target = re.search(r'<a\b[^>]*href="(?:packaging|brands)\.html"', nav)
            return nav[:target.start()]+link+nav[target.start():] if target else nav.replace('</nav>', link+'</nav>')
        text = re.sub(r'<nav\b[^>]*class="portal-nav"[^>]*>.*?</nav>', navigation, text, count=1, flags=re.S)
        if path.name == 'index.html':
            text = re.sub(r'<!-- tonko-catalog -->.*?<!-- /tonko-catalog -->', '', text, flags=re.S)
            marker = '<!-- tonko-packaging -->'
            if marker in text:
                text = text.replace(marker, entry+marker, 1)
            else:
                text = text.replace('</main>', entry+'</main>', 1)
        if path.name == 'sources.html':
            text = re.sub(r'<!-- catalog-sources -->.*?<!-- /catalog-sources -->', '', text, flags=re.S)
            text = text.replace('</main>', f'''<!-- catalog-sources --><section class="portal-container experience-related"><h2>Каталог и цены</h2><p>Источник моделей, фотографий и рублёвых цен — <a href="https://xn--80ajrmkna.xn--p1ai/" target="_blank" rel="noopener noreferrer">интернет-магазин «Лоретта»</a>. Собраны разделы колготок и чулок с объединением повторяющихся моделей. Проверено моделей: {count}; брендов: {brands}. Дата проверки указана в карточках. Описания ТОНКО кратко передают характеристики, а изображения сохраняют подпись источника.</p><p>Доллары — приблизительный пересчёт по официальному курсу <a href="https://www.cbr.ru/currency_base/daily/" target="_blank" rel="noopener noreferrer">Банка России</a>; дата курса показана в каталоге. Сумма заказа, наличие размеров и доставка проверяются у продавца.</p><a href="catalog.html">Открыть каталог →</a></section><!-- /catalog-sources --></main>''', 1)
        if path.name == 'brands.html':
            text = re.sub(r'<!-- catalog-brands -->.*?<!-- /catalog-brands -->', '', text, flags=re.S)
            text = text.replace('</main>', f'<!-- catalog-brands --><section class="portal-container experience-related"><h2>Бренды в каталоге с ценами</h2><p>{brands} брендов колготок и чулок: фотографии моделей, цены в рублях и долларах, фильтры по типу и цене.</p><a href="catalog.html">Сравнить модели и цены →</a></section><!-- /catalog-brands --></main>', 1)
        if text != old:
            path.write_text(text, 'utf-8')
    print(f'Catalogue linked: {count} models, {brands} brands')


if __name__ == '__main__':
    main()
