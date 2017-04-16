import unittest
from majestic import load_settings
from majestic.templating import jinja_environment, absolute_urls, rfc822_date

from datetime import datetime
import locale
import os
from pathlib import Path

import pytz
import jinja2


TESTS_DIR = Path(__file__).resolve().parent
MAJESTIC_DIR = TESTS_DIR.parent.joinpath('majestic')
TEST_BLOG_DIR = TESTS_DIR.joinpath('test-blog')


class TestTemplating(unittest.TestCase):
    """Test functions concerned with loading and rendering templates"""
    def setUp(self):
        os.chdir(str(TEST_BLOG_DIR))
        settings_path = TEST_BLOG_DIR.joinpath('settings.json')
        self.settings = load_settings(files=[settings_path], local=False)
        loader = jinja2.FileSystemLoader([
            self.settings['paths']['templates root'],           # user
            str(MAJESTIC_DIR.joinpath('default_templates'))     # defaults
            ])
        self.jinja_env = jinja2.Environment(loader=loader)

    def test_jinja_environment_basic(self):
        """jinja_environment returns Environment with expected templates"""
        env = jinja_environment(
            user_templates=self.settings['paths']['templates root'],
            settings=self.settings)
        self.assertEqual(self.jinja_env.list_templates(), env.list_templates())

    def test_jinja_environment_defaults(self):
        """jinja_environment results contains expected default options

        In particular:
            environment.auto_reload should be False
            environment.globals should contain 'settings'
        """
        env = jinja_environment(
            user_templates=self.settings['paths']['templates root'],
            settings=self.settings)
        self.assertFalse(env.auto_reload)
        self.assertTrue('settings' in env.globals)

    def test_jinja_environment_custom_options(self):
        """jinja_environment properly applies custom jinja options"""
        self.settings['jinja']['trim_blocks'] = True
        env = jinja_environment(
            user_templates=self.settings['paths']['templates root'],
            settings=self.settings)
        self.assertTrue(env.trim_blocks)

    def test_jinja_environment_default_templates(self):
        """jinja_environment includes default templates in search path

        majestic supplies some default templates that the user is not
        expected to create. These are stored in the majestic directory
        and the folder containing them should be included in the
        search path passed to the jinja loader.
        """
        env = jinja_environment(
            user_templates=self.settings['paths']['templates root'],
            settings=self.settings)
        self.assertIn(str(MAJESTIC_DIR.joinpath('default_templates')),
                      env.loader.searchpath)

    def test_jinja_environment_rfc822_filter(self):
        """jinja_environment adds rfc822_date as a custom filter"""
        env = jinja_environment(
            user_templates=self.settings['paths']['templates root'],
            settings=self.settings)
        self.assertEqual(env.filters['rfc822_date'], rfc822_date)

    def test_jinja_environment_absolute_urls_filter(self):
        """jinja_environment adds absolute_urls as a custom filter"""
        env = jinja_environment(
            user_templates=self.settings['paths']['templates root'],
            settings=self.settings)
        self.assertEqual(env.filters['absolute_urls'], absolute_urls)


class TestRFC822Date(unittest.TestCase):
    """Test the rfc822_date function"""
    def test_rfc822_date_basic(self):
        """Given an aware datetime, return the rfc822-format date"""
        date = pytz.utc.localize(datetime(2015, 9, 19, 14, 43))
        expected = 'Sat, 19 Sep 2015 14:43:00 +0000'
        result = rfc822_date(date)
        self.assertEqual(expected, result)

    def test_rfc822_date_locale(self):
        """Return rfc822-format date in non-English locale

        RFC 822 dates include weekdays and months in English.
        Check that the function is not cheating by using
        strftime for the whole date string.
        """
        starting_locale = locale.getlocale()
        locale.setlocale(locale.LC_ALL, 'de_DE.UTF-8')

        date = pytz.utc.localize(datetime(2015, 9, 19, 14, 43))
        expected = 'Sat, 19 Sep 2015 14:43:00 +0000'
        result = rfc822_date(date)

        locale.setlocale(locale.LC_ALL, starting_locale)       # Restore locale

        self.assertEqual(expected, result)


class TestAbsoluteURLs(unittest.TestCase):
    """Test the absolute_urls function

    asbolute_urls should take HTML and return it with relative URLs
    changed to absolute URLs, using the given base URL.
    """
    def setUp(self):
        self.base_url = 'http://example.com'

    def test_absolute_urls_href(self):
        """absolute_urls changes relative URLs in href attributes

        example:
            <a href="/my/great/page.html">
        becomes:
            <a href="http://example.com/my/great/page.html">
        """
        html = '''\
<head>
<link href="/resources/my-stylesheet.css">
</link></head>
<p><a href="/latin">Lorem ipsum</a>.</p>
        '''.strip()
        expected = '''\
<head>
<link href="http://example.com/resources/my-stylesheet.css">
</link></head>
<p><a href="http://example.com/latin">Lorem ipsum</a>.</p>
        '''.strip()
        result = absolute_urls(html=html, base_url=self.base_url)
        self.assertEqual(expected, result)

    def test_absolute_urls_src(self):
        """absolute_urls changes relative URLs in src attributes

        example:
            <img src="/my/great/image.jpg">
        becomes:
            <img src="http://example.com/my/great/image.jpg">
        """
        html = '''\
<p><img src="/my/great/image.jpg"/></p>
<p><audio src="/my/great/song.mp3"></audio></p>
        '''.strip()
        expected = '''\
<p><img src="http://example.com/my/great/image.jpg"/></p>
<p><audio src="http://example.com/my/great/song.mp3"></audio></p>
        '''.strip()
        result = absolute_urls(html=html, base_url=self.base_url)
        self.assertEqual(expected, result)
