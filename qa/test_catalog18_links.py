import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from catalog_links import link_catalog


def package(**changes):
    return {'id': 'pack-1', 'brand': 'OMSA', 'title': 'Attiva 20 OMSA', 'den': 20,
            'source': 'https://other.example/attiva', **changes}


def product(**changes):
    return {'id': 'loretta-1', 'brand': 'Omsa', 'model': 'Attiva 20', 'title': 'Omsa Attiva 20',
            'productKind': 'колготки', 'den': 20, 'priceRub': 456, 'source': 'https://xn--80ajrmkna.xn--p1ai/product', **changes}


class ExactPriceLinkTests(unittest.TestCase):
    def test_exact_model_with_brand_prefix_or_suffix_links(self):
        result = link_catalog([package()], {'items': [product()]})
        self.assertEqual(result['matches']['pack-1']['priceRub'], 456)
        self.assertEqual(result['matches']['pack-1']['matchType'], 'model')
        self.assertEqual(result['packageByCatalog']['loretta-1'], 'pack-1')

    def test_other_size_density_type_and_brand_never_borrow_price(self):
        for changes in ({'model': 'Attiva 20 XL'}, {'den': 40}, {'brand': 'Sisi'},
                        {'productKind': 'чулки'}, {'den': None}):
            with self.subTest(changes=changes):
                self.assertEqual(link_catalog([package()], {'items': [product(**changes)]})['matches'], {})

    def test_primary_exact_url_can_identify_another_packaging_title(self):
        row = product()
        p = package(source=row['source'], title='Attiva classic')
        self.assertEqual(link_catalog([p], {'items': [row]})['matches']['pack-1']['matchType'], 'source')

    def test_multiple_retailer_models_with_same_identity_are_ambiguous(self):
        rows = [product(), product(id='loretta-2', source='https://xn--80ajrmkna.xn--p1ai/other')]
        self.assertEqual(link_catalog([package()], {'items': rows})['matches'], {})

    def test_variant_source_does_not_transfer_price_to_primary_package(self):
        row = product(model='Attiva 20 XL')
        p = package(variants=[{'source': row['source'], 'title': row['title']}])
        self.assertEqual(link_catalog([p], {'items': [row]})['matches'], {})

    def test_missing_price_remains_unknown_and_input_is_unchanged(self):
        cat = {'items': [product(priceRub=None)]}
        before = copy.deepcopy(cat)
        self.assertIsNone(link_catalog([package()], cat)['matches']['pack-1']['priceRub'])
        self.assertEqual(cat, before)


if __name__ == '__main__':
    unittest.main()
