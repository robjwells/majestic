import unittest

import majestic
import majestic.md as md


class TestMarkdown(unittest.TestCase):
    """Test the majestic package's markdown module"""
    def setUp(self):
        self.settings = majestic.load_settings(local=False)

    def test_get_markdown(self):
        """get_markdown returns a Markdown instance"""
        self.assertEqual(
            type(md.get_markdown(settings=self.settings)).__name__,
            'Markdown'
            )

    def test_render_html(self):
        """Returned Markdown instance converts as expected"""
        original='*abc*'
        expected = '<p><em>abc</em></p>'
        self.assertEqual(
            md.get_markdown(self.settings).convert(original),
            expected)

    def test_convert_extensions(self):
        """Text is rendered with specified Markdown extensions"""
        original = "here's some 'quoted' text"
        expected = '<p>here&rsquo;s some &lsquo;quoted&rsquo; text</p>'

        self.settings['markdown']['extensions'].update(
            {'markdown.extensions.smarty': {}})
        rendered = md.get_markdown(self.settings).convert(original)
        self.assertEqual(expected, rendered)

    def test_convert_html_extensions_config(self):
        """Markdown extension config is used"""
        original = '<<abc>>'
        expected = '<p>&laquo;abc&raquo;</p>'

        self.settings['markdown']['extensions'].update({
            'markdown.extensions.smarty': {'smart_angled_quotes': True}
            })
        rendered = md.get_markdown(self.settings).convert(original)
        self.assertEqual(expected, rendered)

if __name__ == '__main__':
    unittest.main(verbosity=2)
