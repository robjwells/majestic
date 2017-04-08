from datetime import datetime, timedelta
import json
import locale
import os
from pathlib import Path
import random
import shutil
import string
import tempfile
import time
import unittest

import jinja2
import pytz

import majestic

MAJESTIC_DIR = Path(__file__).resolve().parent
TEST_BLOG_DIR = MAJESTIC_DIR.joinpath('test-blog')

# Timing report code
# import time
# @classmethod
# def setUpClass(class_):
#     class_.start_time = time.time()
#
# @classmethod
# def tearDownClass(class_):
#     elapsed = round(time.time() - class_.start_time, 3)
#     print('\n{0:<30}{1:.3f}s'.format(class_.__name__, elapsed))
#
# unittest.TestCase.setUpClass = setUpClass
# unittest.TestCase.tearDownClass = tearDownClass


class TestLoadSettings(unittest.TestCase):
    """Default and site-specific settings tests"""
    def setUp(self):
        os.chdir(str(MAJESTIC_DIR))

    def test_load_default_settings(self):
        """Config class contains setting set only in default config file"""
        settings = majestic.load_settings(default=True, local=False)
        self.assertTrue(settings['testing']['default cfg loaded'])

    def test_load_specific_only_str(self):
        """When given filenames (as str), load only those files"""
        test_settings_fn = str(TEST_BLOG_DIR.joinpath('settings.json'))
        settings = majestic.load_settings(default=False, local=False,
                                          files=[test_settings_fn])
        self.assertTrue(settings['testing']['test-blog cfg loaded'])

    def test_load_specific_only_Path(self):
        """When given filenames (as pathlib.Path), load only those files

        Tests that load_settings correctly handles paths given as
        pathlib.Path instead of str (as os functions expect).
        The burden of conversion should fall on the function
        itself, not its callers.
        """
        test_settings_fn = TEST_BLOG_DIR.joinpath('settings.json')
        settings = majestic.load_settings(default=False, local=False,
                                          files=[test_settings_fn])
        self.assertTrue(settings['testing']['test-blog cfg loaded'])

    def test_load_default_and_local(self):
        """Properly load defaults and settings.json in current directory"""
        os.chdir(str(TEST_BLOG_DIR))
        settings = majestic.load_settings(default=True, local=True)
        self.assertTrue(settings['testing']['test-blog cfg loaded'])
        self.assertTrue(settings['testing']['default cfg loaded'])

    def test_defaults_overriden_by_local(self):
        """Config files loaded in order so that locals override defaults"""
        default_settings = majestic.load_settings(default=True, local=False)
        overridden_value = default_settings['testing']['overridden setting']
        self.assertFalse(overridden_value)
        os.chdir(str(TEST_BLOG_DIR))
        combined_settings = majestic.load_settings()
        overridden_value = combined_settings['testing']['overridden setting']
        self.assertTrue(overridden_value)

    def test_settings_empty_when_not_given_anything(self):
        """Returned config object should be empty when everything disabled"""
        settings = majestic.load_settings(default=False, local=False)
        self.assertFalse(settings)


class TestLoadContentFiles(unittest.TestCase):
    """Test loading of markdown files"""
    def test_markdown_files_posts(self):
        """markdown_files generates expected list for test-blog/posts"""
        posts_dir = TEST_BLOG_DIR.joinpath('posts')
        extensions = ['.md', '.mkd', '.mdown', '.mkdown', '.markdown']

        test_files = []
        for path, dirs, files in os.walk(str(posts_dir)):
            for f in files:
                if os.path.splitext(f)[1] in extensions:
                    test_files.append(os.path.join(path, f))
        test_files = list(map(Path, test_files))
        returned_files = list(majestic.markdown_files(posts_dir))
        test_files.sort()
        returned_files.sort()
        self.assertEqual(test_files, returned_files)

    def test_markdown_files_empty_dir(self):
        """result is empty when given empty dir"""
        temp_dir = Path(tempfile.mkdtemp())
        files = majestic.markdown_files(temp_dir)
        self.assertFalse(list(files))
        temp_dir.rmdir()

    def test_markdown_files_nonempty_dir_no_md(self):
        """result is empty when given nonempty dir containing no md files"""
        temp_dir = Path(tempfile.mkdtemp())
        for x in range(20):
            temp_dir.touch(x)
        files = majestic.markdown_files(temp_dir)
        self.assertFalse(list(files))
        for file in temp_dir.iterdir():
            file.unlink()
        temp_dir.rmdir()


class TestContent(unittest.TestCase):
    """Test the Content base class"""
    def setUp(self):
        """Set dummy values for use in testing"""
        self.title = "Here’s a — test! — dummy title: (with lots o' symbols)"
        self.naive_date = datetime(2015, 8, 22, 9, 46)
        self.slug = 'test-slug-with-no-relation-to-title'
        self.meta = {'tags': ['a', 'b']}
        self.body = (
            # http://slipsum.com
            "You see? It's curious. Ted did figure it out - time"
            "travel. And when we get back, we gonna tell everyone. How"
            "it's possible, how it's done, what the dangers are."
            "\n\n"
            "The lysine contingency - it's intended to prevent the"
            "spread of the animals is case they ever got off the"
            "island. Dr. Wu inserted a gene that makes a single faulty"
            "enzyme in protein metabolism."
            )
        settings_path = TEST_BLOG_DIR.joinpath('settings.json')
        self.settings = majestic.load_settings(files=[settings_path],
                                               local=False)
        # Dummy source / output files for modification date tests
        self.oldest_file = Path(TEST_BLOG_DIR, 'test_file_oldest')
        self.middle_file = Path(TEST_BLOG_DIR, 'test_file_middle')
        self.newest_file = Path(TEST_BLOG_DIR, 'test_file_newest')

    @classmethod
    def setUpClass(self):
        """Set up modification date test files

        These files are touched to ensure the date difference between
        them is correct. Sleep for 1 second because of HFS+ resolution.
        """
        Path(TEST_BLOG_DIR, 'test_file_oldest').touch()
        time.sleep(1)
        Path(TEST_BLOG_DIR, 'test_file_middle').touch()
        time.sleep(1)
        Path(TEST_BLOG_DIR, 'test_file_newest').touch()

    def test_content_init_basic(self):
        """Content init properly sets core attributes

        Core attributes are those all content requires as a minimum:
            * title
            * body
            * settings

        No other attributes are required.
        """
        content = majestic.Content(title=self.title, body=self.body,
                                   settings=self.settings)
        self.assertEqual([self.title, self.body, self.settings],
                         [content.title, content.body, content._settings])

    def test_content_init_meta(self):
        """Content stores extra kwargs as the .meta attribute"""
        content = majestic.Content(title=self.title, body=self.body,
                                   settings=self.settings, foo='bar')
        self.assertEqual(content.meta['foo'], 'bar')

    def test_content_init_slug(self):
        """Content stores a valid slug as the slug attribute

        Slug validity is defined elsewhere, but this test uses the
        simplest possible slug, a single alphabetical character.
        """
        content = majestic.Content(title=self.title, body=self.body,
                                   slug='a', settings=self.settings)
        self.assertEqual(content.slug, 'a')

    def test_content_init_slug_from_title(self):
        """Content creates a slug from the title one is not given

        Slug validity is defined elsewhere, but this test uses the
        simplest possible title for the source, a single alphabetical
        character.
        """
        content = majestic.Content(title='a', body=self.body,
                                   settings=self.settings)
        self.assertEqual(content.slug, 'a')

    def test_content_init_invalid_slug(self):
        """Content normalises invalid slugs before storing them"""
        invalid_slug = '!not:valid!'
        expected = 'not-valid'
        content = majestic.Content(title='a', body=self.body,
                                   settings=self.settings, slug=invalid_slug)
        self.assertEqual(content.slug, expected)

    def test_content_init_modification_date(self):
        """Content sets init arg modification_date as an attribute"""
        mod_date = datetime(2015, 1, 25, 9, 30)
        content = majestic.Content(title=self.title, body=self.body,
                                   slug=self.slug, settings=self.settings,
                                   modification_date=mod_date)
        self.assertEqual(content.modification_date, mod_date)

    def test_content_init_mod_date_from_source_path(self):
        """Content sets modification date from source file (if provided)"""
        expected_mod_date = datetime.fromtimestamp(
            self.middle_file.stat().st_mtime)
        content = majestic.Content(title=self.title, body=self.body,
                                   slug=self.slug, settings=self.settings,
                                   source_path=self.middle_file)
        self.assertEqual(content.modification_date, expected_mod_date)

    def test_content_init_save_as(self):
        """Content overrides .path_part if given save_as argument

        save_as should be a string which is joined onto the output
        root or site URL when accessing .output_path or .url

        It's sufficient just to check that .path_part is set to the
        save_as argument as the .output_path and .url properties are
        tested separately.

        If this is not implemented or broken, expect the test to cause
        BlogObject to raise NotImplementedError. This is because the
        ordinary .path_part getter fetches the class's _path_template_key,
        which is not implemented (well, it is as a property that raises)
        on BlogObject or its abstract subclasses.
        """
        custom_path = '404.html'
        content = majestic.Content(title=self.title, body=self.body,
                                   settings=self.settings,
                                   save_as=custom_path)
        self.assertEqual(content.path_part, custom_path)

    def test_content_is_new_no_output_file(self):
        """Content.is_new is True when no corresponding output file exists

        If there is no output file the content object is always considered
        new, even if it doesn't have a source file and wasn't created with
        an explicit modification date (ie programmatically).
        """
        content = majestic.Content(title=self.title, body=self.body,
                                   slug=self.slug, settings=self.settings)
        # Override output path to ensure file does not exist
        content.output_path = Path('/tmp/test-majestic-no-file-here')
        self.assertTrue(content.is_new)

    def test_content_is_new_true_with_output_file(self):
        """Content.is_new is True when an older output file exists"""
        content = majestic.Content(title=self.title, body=self.body,
                                   slug=self.slug, settings=self.settings,
                                   source_path=self.newest_file)
        # Override output path
        content.output_path = self.oldest_file
        self.assertTrue(content.is_new)

    def test_content_is_new_false_with_output_file(self):
        """Content.is_new is False when a newer output file exists"""
        content = majestic.Content(title=self.title, body=self.body,
                                   slug=self.slug, settings=self.settings,
                                   source_path=self.oldest_file)
        # Override output path
        content.output_path = self.newest_file
        self.assertFalse(content.is_new)

    def test_content_is_new_raises(self):
        """Content.is_new raises if mod date is None and output file exists"""
        content = majestic.Content(title=self.title, body=self.body,
                                   slug=self.slug, settings=self.settings)
        content.output_path = self.newest_file
        with self.assertRaises(majestic.ModificationDateError):
            content.is_new

    def test_content_is_new_setter(self):
        """Content.is_new is a property that can be set"""
        content = majestic.Content(title=self.title, body=self.body,
                                   slug=self.slug, settings=self.settings)
        content.is_new = True
        self.assertTrue(content.is_new)

    def test_content_lt_title(self):
        """Content with different titles compare properly"""
        post_1 = majestic.Content(title='title a',
                                  slug=self.slug, body=self.body,
                                  settings=self.settings)
        post_2 = majestic.Content(title='title b',
                                  slug=self.slug, body=self.body,
                                  settings=self.settings)
        self.assertTrue(post_1 < post_2)
        self.assertFalse(post_2 < post_1)

    def test_content_compare_title_case_insensitive(self):
        """Content with titles that differ in case compare properly"""
        post_1 = majestic.Content(title='title a',
                                  slug=self.slug, body=self.body,
                                  settings=self.settings)
        post_2 = majestic.Content(title='title B',
                                  slug=self.slug, body=self.body,
                                  settings=self.settings)
        self.assertTrue(post_1 < post_2)

    def test_content_lt_slug(self):
        """Content with different slugs compare properly"""
        post_1 = majestic.Content(title=self.title,
                                  slug='test-a', body=self.body,
                                  settings=self.settings)
        post_2 = majestic.Content(title=self.title,
                                  slug='test-b', body=self.body,
                                  settings=self.settings)
        self.assertTrue(post_1 < post_2)
        self.assertFalse(post_2 < post_1)


class TestMarkdown(unittest.TestCase):
    """Test the markdown module wrappers"""
    def setUp(self):
        """Set dummy values for use in testing"""
        settings_path = TEST_BLOG_DIR.joinpath('settings.json')
        self.settings = majestic.load_settings(files=[settings_path],
                                               local=False)
        self.title = 'Test Title'

    def test_render_html(self):
        """Content.html returns the body converted to HTML"""
        content = majestic.Content(title=self.title, settings=self.settings,
                                   body='*abc*')
        expected = '<p><em>abc</em></p>'
        self.assertEqual(expected, content.html)

    def test_render_html_extensions(self):
        """Content.html is rendered with specified Markdown extensions"""
        original = "here's some 'quoted' text"
        plain_html = "<p>here's some 'quoted' text</p>"
        with_smarty = '<p>here&rsquo;s some &lsquo;quoted&rsquo; text</p>'

        self.settings['markdown']['extensions'] = {}
        content = majestic.Content(title=self.title, settings=self.settings,
                                   body=original)
        self.assertEqual(plain_html, content.html)

        self.settings['markdown']['extensions'].update(
            {'markdown.extensions.smarty': {}})
        content = majestic.Content(title=self.title, settings=self.settings,
                                   body=original)
        self.assertEqual(with_smarty, content.html)

    def test_render_html_extensions_config(self):
        """Markdown extension config is used"""
        original = '<<abc>>'
        with_smarty = '<p>&laquo;abc&raquo;</p>'

        self.settings['markdown']['extensions'].update({
            'markdown.extensions.smarty': {'smart_angled_quotes': True}
            })
        content = majestic.Content(title=self.title, settings=self.settings,
                                   body=original)
        self.assertEqual(with_smarty, content.html)


class TestPage(unittest.TestCase):
    """Test the Page content classes"""
    def setUp(self):
        """Set dummy values for use in testing"""
        self.title = "Here’s a — test! — dummy title: (with lots o' symbols)"
        self.naive_date = datetime(2015, 8, 22, 9, 46)
        self.slug = 'test-slug-with-no-relation-to-title'
        self.meta = {'tags': ['a', 'b']}
        self.body = (
            # http://slipsum.com
            "You see? It's curious. Ted did figure it out - time"
            "travel. And when we get back, we gonna tell everyone. How"
            "it's possible, how it's done, what the dangers are."
            "\n\n"
            "The lysine contingency - it's intended to prevent the"
            "spread of the animals is case they ever got off the"
            "island. Dr. Wu inserted a gene that makes a single faulty"
            "enzyme in protein metabolism."
            )
        settings_path = TEST_BLOG_DIR.joinpath('settings.json')
        self.settings = majestic.load_settings(files=[settings_path],
                                               local=False)
        # Avoid index.html trimming mismatch in url tests
        self.settings['paths']['page path template'] = '{content.slug}.html'

    def test_page_inheritance(self):
        """Page instances are also an instance of Content"""
        page = majestic.Page(title=self.title, body=self.body,
                             settings=self.settings)
        self.assertTrue(isinstance(page, majestic.Content))

    def test_page_output_path_and_url(self):
        """Page defines output_path and url properties

        Output path should be a pathlib.Path object, url a str
        """
        page = majestic.Page(title=self.title, body=self.body,
                             settings=self.settings, slug='abc')

        path_template = self.settings['paths']['page path template']
        path = path_template.format(content=page)

        output_dir = self.settings['paths']['output root']
        site_url = self.settings['site']['url']

        expected_output = Path(output_dir, path)
        expected_url = site_url + '/' + path

        self.assertEqual(expected_output, page.output_path)
        self.assertEqual(expected_url, page.url)

    def test_page_path_part(self):
        """path_part correctly formats and stores Page's path part

        Path part here refers to the 'path' section of a URL, for example:
            http://example.com/path/part.html
        This is the same as the path underneath the output root directory:
            /.../blog/output/path/part.html

        Since both are identical it is sensible for the path to be created
        in one place in the class and stored, with .output_path and .url
        both looking in one place for them.
        """
        page = majestic.Page(title=self.title, body=self.body,
                             settings=self.settings, slug='abc')

        path_template = self.settings['paths']['page path template']
        path = path_template.format(content=page)
        self.assertEqual(path, page.path_part)

    def test_Page_eq(self):
        """Two distinct Page objects with same attrs compare equal

        Page doesn't have its own __eq__ implementation as it's just
        a concrete version of Content, but Page does properly handle
        calls to self.output_path and self.url, while Content raises
        NotImplementedError (correctly).

        Since Content is not meant to be instantiated, it's fair to
        test the superclass's implementation of __eq__ through a
        subclass. (And __eq__ belongs on the superclass because
        otherwise both Page and Post would have to implement almost
        exactly the same method.)
        """
        page_a = majestic.Page(title=self.title, body=self.body,
                               settings=self.settings)
        page_b = majestic.Page(title=self.title, body=self.body,
                               settings=self.settings)
        page_c = majestic.Page(title='different', body=self.body,
                               settings=self.settings)
        self.assertEqual(page_a, page_b)
        self.assertNotEqual(page_a, page_c)


class TestPost(unittest.TestCase):
    """Test the Post content class"""
    def setUp(self):
        """Set dummy values for use in testing"""
        self.title = "Here’s a — test! — dummy title: (with lots o' symbols)"
        self.slug = 'test-slug-with-no-relation-to-title'
        self.meta = {'tags': ['a', 'b']}
        self.body = (
            # http://slipsum.com
            "You see? It's curious. Ted did figure it out - time"
            "travel. And when we get back, we gonna tell everyone. How"
            "it's possible, how it's done, what the dangers are."
            "\n\n"
            "The lysine contingency - it's intended to prevent the"
            "spread of the animals is case they ever got off the"
            "island. Dr. Wu inserted a gene that makes a single faulty"
            "enzyme in protein metabolism."
            )
        settings_path = TEST_BLOG_DIR.joinpath('settings.json')
        self.settings = majestic.load_settings(files=[settings_path],
                                               local=False)

        # Avoid index.html trimming mismatch in url tests
        self.settings['paths']['post path template'] = (
            '{content.date:%Y/%m}/{content.slug}.html')

        # Override timezone for testing purposes
        self.settings['dates']['timezone'] = 'Europe/London'
        self.tz = pytz.timezone('Europe/London')
        self.naive_date = datetime(2015, 8, 22, 9, 46)
        self.aware_date = self.tz.localize(self.naive_date)
        self.date_string = '2015-08-22 09:46'

    def test_post_inheritance(self):
        """Post instances are also an instance of Content"""
        post = majestic.Post(title=self.title, body=self.body,
                             date=self.naive_date, settings=self.settings)
        self.assertTrue(isinstance(post, majestic.Content))

    def test_post_init_date(self):
        """Post stores provided date as self.date"""
        post = majestic.Post(title=self.title, body=self.body,
                             date=self.naive_date, settings=self.settings)
        self.assertEqual(self.aware_date, post.date)

    def test_post_init_date_string(self):
        """If given a str for date, Post parses it into a datetime object"""
        self.settings['dates']['format'] = '%Y-%m-%d %H:%M'
        post = majestic.Post(title=self.title, body=self.body,
                             date=self.date_string, settings=self.settings)
        self.assertEqual(self.aware_date, post.date)

    def test_date_has_timezone(self):
        """Post correctly localizes the provided date"""
        post = majestic.Post(title=self.title, body=self.body,
                             date=self.naive_date, settings=self.settings)
        self.assertEqual(post.date, self.aware_date)

    def test_Post_eq(self):
        """Two distinct Posts with same attrs compare equal

        And also that two Posts with differing dates compare unequal:
        to check that Post is not just relying on its superclass's
        implementation.

        The overriding of the post path template is so that all the
        posts have the same output_path/url and we can be sure that
        the date itself is being compared.
        """
        new_path = '{content.date.year}/{content.slug}'
        self.settings['paths']['post path template'] = new_path
        post_a = majestic.Post(title=self.title, body=self.body,
                               settings=self.settings, date=self.naive_date)
        post_b = majestic.Post(title=self.title, body=self.body,
                               settings=self.settings, date=self.naive_date)
        post_c = majestic.Post(title=self.title, body=self.body,
                               settings=self.settings,
                               date=datetime(2015, 1, 1))
        self.assertEqual(post_a, post_b)
        self.assertNotEqual(post_a, post_c)

    def test_post_compare_lt_dates(self):
        """Posts with different dates compare properly"""
        post_1 = majestic.Post(title=self.title, body=self.body,
                               settings=self.settings,
                               date=datetime(2015, 1, 1))
        post_2 = majestic.Post(title=self.title, body=self.body,
                               settings=self.settings,
                               date=datetime(2014, 1, 1))
        self.assertLess(post_2, post_1)

    def test_post_compare_lt_identical_dates(self):
        """Posts with the same date but different titles compare properly

        The Post class should only test the dates, and delegate title and
        slug comparison to its superclass.
        """
        post_1 = majestic.Post(title='title a', body=self.body,
                               date=self.naive_date, settings=self.settings)
        post_2 = majestic.Post(title='title B', body=self.body,
                               date=self.naive_date, settings=self.settings)
        self.assertLess(post_1, post_2)

    def test_post_future_date_raises_DraftPost(self):
        """Initialising a Post with a future date raises DraftError"""
        with self.assertRaises(majestic.DraftError):
            majestic.Post(title=self.title, body=self.body,
                          settings=self.settings,
                          date=datetime(2100, 1, 1))

    def test_post_output_path_and_url(self):
        """Post defines output_path and url properties

        Output path should be a pathlib.Path object, url a str
        """
        post = majestic.Post(title=self.title, body=self.body,
                             settings=self.settings, date=self.naive_date)

        path_template = self.settings['paths']['post path template']
        path = path_template.format(content=post)

        output_dir = self.settings['paths']['output root']
        site_url = self.settings['site']['url']

        expected_output = Path(output_dir, path)
        expected_url = site_url + '/' + path

        self.assertEqual(expected_output, post.output_path)
        self.assertEqual(expected_url, post.url)


class TestSlugFunctions(unittest.TestCase):
    """Test validate_slug and normalise_slug

    Slugs containing any characters not considered 'unreserved'
    by RFC 3986 are deemed to be invalid.

    The acceptable characters, aside from percent-encoded
    characters, are:

    a-z A-Z 0-9 - . _ ~

    Note that only ASCII alphabetic characters are allowed. (Covered by
    the inclusive ranges 0x41-0x5A and 0x61-0x7A.)

    Slugs containing a percent character that is not followed by
    two hex digits are also deemed to be invalid.

    A normalised slug contains only the following characters (the
    unreserved set excluding capital ASCII letters, the period,
    underscore and tilde):

    a-z 0-9 -

    A file's slug *is not* checked against the normalised characters.
    It is only normalised if it contains characters outside the
    unreserved set.

    Relatively, the validator is liberal and the normaliser conservative.
    The normaliser also removes percent-encoded characters (%20).

    The unreserved characters are defined in IETF RFC 3986,
    Uniform Resource Identifier (URI): Generic Syntax,
    specifically section 2.3. Unreserved Characters.
    """
    def test_normalise_slug_known_bad(self):
        """normalise_slug correctly normalises known bad slug"""
        known_bad_slug = "This is a completely invalid slug :/?#[]@!$&'()*+,;="
        expected = 'this-is-a-completely-invalid-slug'
        new_slug = majestic.normalise_slug(known_bad_slug)
        self.assertEqual(new_slug, expected)

    def test_normalise_slug_chars(self):
        """normalise_slug function returns a valid slug

        A valid slug is deemed to contain only the following characters:

        a-z 0-9 - . _ ~
        """
        bad_set = set(" :/?#[]@!$&'()*+,;=")
        good_set = set(string.ascii_lowercase + string.digits + '-')

        test_bad_slug = "this is an :/?#[]@!$&'()*+,;= invalid slug"
        new_slug = majestic.normalise_slug(test_bad_slug)
        self.assertTrue(set(new_slug).issubset(good_set))
        self.assertTrue(set(new_slug).isdisjoint(bad_set))

        test_good_slug = "00-this-is-a-valid-slug"
        self.assertEqual(majestic.normalise_slug(test_good_slug),
                         test_good_slug)

    def test_normalise_slug_empty_string(self):
        """normalise_slug should raise if result is the empty string"""
        with self.assertRaises(ValueError):
            majestic.normalise_slug(":/?#[]@!$&'()*+,;=")

    def test_normalise_slug_conservative(self):
        """Normalise correctly removes unreserved chars . _ ~

        Those characters pass the validator but should still be removed
        if the slug is normalised because of another character.
        """
        slug = 'here are some valid chars . _ ~ and an invalid one!'
        normalised = majestic.normalise_slug(slug)
        self.assertEqual(
            normalised,
            'here-are-some-valid-chars-and-an-invalid-one'
            )

    def test_normalise_slug_percent_encoding(self):
        """normalise_slug removes percent-encoded characters"""
        slug = 'this%20slug%20has%20spaces'
        normalised = majestic.normalise_slug(slug)
        self.assertEqual(normalised, 'this-slug-has-spaces')

    def test_validate_slug_empty(self):
        """validate_slug returns False if slug is the empty string"""
        self.assertFalse(majestic.validate_slug(''))

    def test_validate_slug_false(self):
        """validate_slug returns False if slug contains invalid characters"""
        known_bad_slug = "This is a completely invalid slug :/?#[]@!$&'()*+,;="
        self.assertFalse(majestic.validate_slug(known_bad_slug))

    def test_validate_slug_bad_percent(self):
        """validate_slug returns False if slug has bad percent encoding"""
        known_bad_slug = "this-is-not-100%-valid"
        self.assertFalse(majestic.validate_slug(known_bad_slug))

    def test_validate_slug_good_percent(self):
        """validate_slug returns True given proper percent encoding"""
        known_good_slug = 'hello%20world'
        self.assertTrue(majestic.validate_slug(known_good_slug))

    def test_validate_slug_true(self):
        """validate_slug returns True when slug contains all valid chars"""
        known_good_slug = "00-this-is_a~valid.slug"
        self.assertTrue(majestic.validate_slug(known_good_slug))

    def test_validate_slug_nonascii(self):
        """validate_slug returns False when slug contains non-ASCII chars

        This is an important test because non-ASCII chars fall between
        the characters in the reserved set and the unreserved set.
        """
        slug = 'lets-go-to-the-café'
        self.assertFalse(majestic.validate_slug(slug))


class TestFromFile(unittest.TestCase):
    """Test that .from_file on Content classes correctly parses files"""
    def setUp(self):
        settings_path = TEST_BLOG_DIR.joinpath('settings.json')
        self.settings = majestic.load_settings(files=[settings_path],
                                               local=False)

        self.pages_path = TEST_BLOG_DIR.joinpath('pages')
        self.posts_path = TEST_BLOG_DIR.joinpath('posts')
        lib_post_names = '''\
1917-11-07 Годовщина Великой Октябрьской социалистической революции.md
1949-10-01 国庆节.mkd
1959-01-01 Triunfo de la Revolución.mdown
1975-04-30 Ngày Thống nhất.markdown
1979-07-19 Liberation Day.mkdown'''.splitlines()
        self.lib_posts = [self.posts_path.joinpath(post)
                          for post in lib_post_names]

    def test_posts_general(self):
        """Posts returned with file's contents correctly stored

        This test tests the five liberation day posts, starting:
            1917-11-07
            1949-10-01
            1959-01-01
            1975-04-30
            1979-07-19

        The parsing rules should differentiate between the metadata and
        body. The metadata is all the lines between the start of the file
        and a blank line. The body is everything following the blank line.

        Of the metadata in the header, the title, slug and date should
        be available as attributes. The date should be a datetime object
        corresponding to the textual date in the metadata header.

        All other metadata should be available in a dictionary stored
        on the post as the meta attribute. The keys in that dictionary
        should be lower-case and stripped of leading and trailing
        whitespace. The values should be stripped only.

        The body should be stripped of leading and trailing newlines only.
        """
        date_format = self.settings['dates']['format']

        for file in self.lib_posts:
            with file.open() as f:
                meta, body = f.read().split('\n\n', maxsplit=1)
            meta = [line.split(':', maxsplit=1) for line in meta.splitlines()]
            meta = {key.lower().strip(): value.strip() for key, value in meta}

            file_dict = meta
            file_dict['body'] = body.strip('\n')
            file_dict['source_path'] = file

            post = majestic.Post.from_file(file, settings=self.settings)
            post_dict = post.meta.copy()
            post_dict['title'] = post.title
            post_dict['slug'] = post.slug
            post_dict['date'] = post.date.strftime(date_format)
            post_dict['body'] = post.body
            post_dict['source_path'] = post.source_path

            self.assertEqual(file_dict, post_dict)

    def test_about_page(self):
        """Parsing basic page should work as with posts"""
        page = majestic.Page.from_file(self.pages_path.joinpath('about.md'),
                                       settings=self.settings)
        self.assertEqual(page.title, 'About majestic')
        self.assertEqual(page.slug, 'about')
        self.assertEqual(
            page.body,
            ('Majestic makes websites out of markdown files.\n\n'
             'It is written in Python and was started by Rob Wells.'))

    def test_parse_known_bad_slug(self):
        """.from_file detects and normalises invalid slugs

        When given a file containing an invalid value for the slug,
        .from_file should return a content object where the slug
        has been normalised.
        """
        known_bad_file = self.posts_path.joinpath('test_invalid_slug.md')
        good_chars = set(string.ascii_lowercase + string.digits + '-')

        post = majestic.Post.from_file(known_bad_file, settings=self.settings)
        self.assertLess(set(post.slug), good_chars)  # Subset test

    def test_parse_bad_percent_encoding(self):
        """.from_file normalises slugs containing invalid percent encoding"""
        bad_percent_file = self.posts_path.joinpath('test_bad_percent.md')
        bad_percent_slug = 'this-is-not-100%-valid'
        post = majestic.Post.from_file(bad_percent_file,
                                       settings=self.settings)
        self.assertNotEqual(post.slug, bad_percent_slug)

    def test_parse_known_good_slug(self):
        """.from_file does not normalise known good slug"""
        known_good_file = self.posts_path.joinpath('test_good_slug.md')
        known_good_slug = 'valid%20slug'

        post = majestic.Post.from_file(known_good_file, settings=self.settings)
        self.assertTrue(post.slug, known_good_slug)

    def test_explicit_draft(self):
        """.from_file raises DraftError given a file with 'draft' in meta

        'draft' should appear (without quotes) on a line by itself
        """
        with self.assertRaises(majestic.DraftError):
            majestic.Post.from_file(
                file=self.posts_path.joinpath('test_explicit_draft.md'),
                settings=self.settings)


class TestTemplating(unittest.TestCase):
    """Test functions concerned with loading and rendering templates"""
    def setUp(self):
        os.chdir(str(TEST_BLOG_DIR))
        settings_path = TEST_BLOG_DIR.joinpath('settings.json')
        self.settings = majestic.load_settings(files=[settings_path],
                                               local=False)
        loader = jinja2.FileSystemLoader([
            self.settings['paths']['templates root'],           # user
            str(MAJESTIC_DIR.joinpath('default_templates'))     # defaults
            ])
        self.jinja_env = jinja2.Environment(loader=loader)

    def test_jinja_environment_basic(self):
        """jinja_environment returns Environment with expected templates"""
        env = majestic.jinja_environment(
            user_templates=self.settings['paths']['templates root'],
            settings=self.settings)
        self.assertEqual(self.jinja_env.list_templates(), env.list_templates())

    def test_jinja_environment_defaults(self):
        """jinja_environment results contains expected default options

        In particular:
            environment.auto_reload should be False
            environment.globals should contain 'settings'
        """
        env = majestic.jinja_environment(
            user_templates=self.settings['paths']['templates root'],
            settings=self.settings)
        self.assertFalse(env.auto_reload)
        self.assertTrue('settings' in env.globals)

    def test_jinja_environment_custom_options(self):
        """jinja_environment properly applies custom jinja options"""
        self.settings['jinja']['trim_blocks'] = True
        env = majestic.jinja_environment(
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
        env = majestic.jinja_environment(
            user_templates=self.settings['paths']['templates root'],
            settings=self.settings)
        self.assertIn(str(MAJESTIC_DIR.joinpath('default_templates')),
                      env.loader.searchpath)

    def test_jinja_environment_rfc822_filter(self):
        """jinja_environment adds rfc822_date as a custom filter"""
        env = majestic.jinja_environment(
            user_templates=self.settings['paths']['templates root'],
            settings=self.settings)
        self.assertEqual(env.filters['rfc822_date'], majestic.rfc822_date)

    def test_jinja_environment_absolute_urls_filter(self):
        """jinja_environment adds absolute_urls as a custom filter"""
        env = majestic.jinja_environment(
            user_templates=self.settings['paths']['templates root'],
            settings=self.settings)
        self.assertEqual(env.filters['absolute_urls'], majestic.absolute_urls)


class TestRFC822Date(unittest.TestCase):
    """Test the rfc822_date function"""
    def test_rfc822_date_basic(self):
        """Given an aware datetime, return the rfc822-format date"""
        date = pytz.utc.localize(datetime(2015, 9, 19, 14, 43))
        expected = 'Sat, 19 Sep 2015 14:43:00 +0000'
        result = majestic.rfc822_date(date)
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
        result = majestic.rfc822_date(date)

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
        result = majestic.absolute_urls(html=html, base_url=self.base_url)
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
        result = majestic.absolute_urls(html=html, base_url=self.base_url)
        self.assertEqual(expected, result)


class TestIndex(unittest.TestCase):
    """Test the Index class

    The Index class largely just holds data:
        page_number:        1 to len(index_pages)
        newer_index_url:    url to an index with more recent posts or None
        older_index_url:    url to an index with less recent posts or None
        output_path:        path the index should be written to (pathlib.Path)
        url:                url of the index (str)
        posts:              [Post] to be rendered on the index page

    An Index created with page_number 1 is always index.html.

    It should also have a .paginate_posts class method that returns
    a list of Index objects.
    """
    def setUp(self):
        settings_path = TEST_BLOG_DIR.joinpath('settings.json')
        self.settings = majestic.load_settings(files=[settings_path],
                                               local=False)
        self.settings['index']['posts per page'] = 2
        path_template = 'page-{content.page_number}.html'
        self.settings['paths']['index pages path template'] = path_template
        self.settings['site']['url'] = 'http://example.com'

        dates = [datetime(2015, 1, 1) + timedelta(i) for i in range(5)]
        titles = ['A', 'B', 'C', 'D', 'E']
        bodies = ['A', 'B', 'C', 'D', 'E']
        self.posts = [
            majestic.Post(title=t, body=b, date=d, settings=self.settings)
            for t, b, d in zip(titles, bodies, dates)
            ]

    def test_Index_paginate_posts_per_index(self):
        """paginate_posts gives each Index the right number of posts"""
        result = majestic.Index.paginate_posts(posts=self.posts,
                                               settings=self.settings)
        for expected_count, index in zip([2, 2, 1], result):
            self.assertEqual(expected_count, len(index.posts))

    def test_Index_paginate_order(self):
        """paginate_posts returns Index objects ordered first to last"""
        result = majestic.Index.paginate_posts(posts=self.posts,
                                               settings=self.settings)
        for expected_number, index in enumerate(result, start=1):
            self.assertEqual(expected_number, index.page_number)

    def test_Index_attrs(self):
        """Each Index returned by paginate_posts has the correct attributes"""
        attr_list = ['page_number', 'newer_index_url', 'older_index_url',
                     'output_path', 'url', 'posts']
        result = majestic.Index.paginate_posts(posts=self.posts,
                                               settings=self.settings)
        for index in result:
            for attribute in attr_list:
                self.assertTrue(hasattr(index, attribute))

    def test_Index_output_path(self):
        """Index properly sets output path"""
        self.settings['paths']['output root'] = ''
        indexes = [
            majestic.Index(page_number=n, settings=self.settings, posts=[])
            for n in range(1, 3)
            ]
        self.assertEqual(Path('index.html'), indexes[0].output_path)
        self.assertEqual(Path('page-2.html'), indexes[1].output_path)

    def test_Index_url(self):
        """Index properly sets URL"""
        base_url = 'http://example.com'
        self.settings['site']['url'] = base_url
        indexes = [
            majestic.Index(page_number=n, settings=self.settings, posts=[])
            for n in range(1, 3)
            ]
        self.assertEqual(base_url, indexes[0].url)
        self.assertEqual(base_url + '/page-2.html', indexes[1].url)

    def test_Index_compare(self):
        """Index objects compare by page number"""
        index_a = majestic.Index(page_number=1, settings=self.settings,
                                 posts=[])
        index_b = majestic.Index(page_number=2, settings=self.settings,
                                 posts=[])
        self.assertLess(index_a, index_b)

    def test_Index_posts_sorted(self):
        """Index sorts posts by newest before storing them"""
        index = majestic.Index(page_number=1, settings=self.settings,
                               posts=self.posts)
        self.assertEqual(sorted(self.posts, reverse=True), index.posts)

    def test_Index_eq(self):
        """Two distinct Index objects with same attrs compare equal"""
        index_a = majestic.Index(page_number=1, settings=self.settings,
                                 posts=self.posts)
        index_b = majestic.Index(page_number=1, settings=self.settings,
                                 posts=self.posts)
        index_c = majestic.Index(page_number=2, settings=self.settings,
                                 posts=self.posts)
        self.assertEqual(index_a, index_b)
        self.assertNotEqual(index_a, index_c)

    def test_Index_iter(self):
        """Index should support iteration over its posts

        Looping over an Index should be equivalent to looping
        its posts list attribute.
        """
        expected = sorted(self.posts, reverse=True)
        index = majestic.Index(page_number=1, settings=self.settings,
                               posts=self.posts)
        self.assertEqual(expected, [p for p in index])

    def test_Index_paginate_posts_result(self):
        """Result of paginate_posts on known date gives expected result"""
        expected = [
            majestic.Index(page_number=1, settings=self.settings,
                           posts=self.posts[-2:]),
            majestic.Index(page_number=2, settings=self.settings,
                           posts=self.posts[-4:-2]),
            majestic.Index(page_number=3, settings=self.settings,
                           posts=self.posts[:-4])
            ]

        expected[0].older_index_url = expected[1].url
        expected[1].older_index_url = expected[2].url
        expected[2].newer_index_url = expected[1].url
        expected[1].newer_index_url = expected[0].url

        result = majestic.Index.paginate_posts(
            posts=self.posts, settings=self.settings)
        self.assertEqual(expected, result)


class TestChunk(unittest.TestCase):
    """Test the chunk function

    Chunk yields the members of its iterable argument in chunks
    of a given length.

    If the length of the iterable is not a multiple of the chunk length,
    the final chunk contains the remaining data but does not fill to
    meet the chunk length (unlike the grouper recipe in the
    itertools documentation).
    """
    def setUp(self):
        self.data = 'ABCDEFGHIJ'

    def test_chunk_5(self):
        """Take chunks of 5 elements from self.data"""
        expected = ['ABCDE', 'FGHIJ']
        result = majestic.chunk(self.data, 5)
        self.assertEqual(expected, list(result))

    def test_chunk_3(self):
        """Take chunks of 3 elements from self.data"""
        expected = ['ABC', 'DEF', 'GHI', 'J']
        result = majestic.chunk(self.data, 3)
        self.assertEqual(expected, list(result))


class TestBlogObject(unittest.TestCase):
    """Test the BlogObject base class

    Superclass for all classes that ultimately represent and will
    produce a file on disk for consumption on the web. (That's all
    html files and the RSS and sitemap XML files.)

    It should provide implementations for all common web/disk-related
    properties and methods:
        * URL
        * Output path
        * Rendering self to a file

    It should require classes to do only the minimum needed support them,
    in particular defining string keys to retrieve the following from
    the settings object:
        * the path template string
        * the jinja template filename

    The BlogObject class should itself raise NotImplementedError when
    the properties for those keys are accessed, making clear the need
    for concrete subclasses to define them. (Exempt from this are
    abstract classes that aren't intended to be written to disk, so
    Content does not define them but Content's subclasses must.)

    It is ultimately content agnostic. In a language with protocols this
    would probably be a protocol with default implementations.
    """
    def setUp(self):
        self.settings = majestic.load_settings(local=False)

        self.test_output_dir = MAJESTIC_DIR.joinpath('output-root')
        self.settings['paths']['output root'] = str(self.test_output_dir)

        self.templates_root = MAJESTIC_DIR.joinpath('test-templates')
        self.settings['paths']['templates root'] = str(self.templates_root)

        self.env = majestic.jinja_environment(
            user_templates=self.templates_root,
            settings=self.settings)

    def tearDown(self):
        """Clean up output-root folder"""
        try:
            self.test_output_dir.rmdir()
        except FileNotFoundError:
            pass

    def test_BlogObject_no_arguments(self):
        """BlogObject should not require arguments to init

        The intention is that BlogObject only contains default method
        implementations to be inherited and has no content of its own.
        """
        self.assertIsInstance(majestic.BlogObject(), majestic.BlogObject)

    def test_BlogObject_properties_exist(self):
        """BlogObject defines expected properties and methods

        Expected:
            * path_part
            * output_path
            * url
            * render_to_disk
        """
        attrs = ['path_part', 'output_path', 'url', 'render_to_disk']
        bo = majestic.BlogObject()
        for a in attrs:
            self.assertIn(a, dir(bo))

    def test_BlogObject_key_props_raise(self):
        """BlogObject key properties should raise NotImplementedError

        key properties in question:
            * _path_template_key
            * _template_file_key

        The intention being that subclasses will define class variables
        that contain the strings needed to index into the settings.

        For example:
            class A(BlogObject):
                _path_template_key = 'a path template'
                _template_file_key = 'a template filename'
        """
        bo = majestic.BlogObject()
        for attr in ['_path_template_key', '_template_file_key']:
            with self.assertRaises(NotImplementedError):
                getattr(bo, attr)

    def test_BlogObject_computed_props_raise(self):
        """Computed properties that depend on unimplemented ones raise

        computed properties in question:
            * output_path
            * url

        To prevent repetition, these properties should depend on a single
        path_part property/method that computes the path part of the url
        (http://siteurl.com/[path/part.html]) and the part of the file
        path below the output root (blog dir/output root/[path/part.html]).

        In turn this should depend on the class setting the _path_template_key
        class variable. Since only subclasses set this, BlogObject should
        raise NotImplementedError (see test_BlogObject_key_props_raise)
        when these properties are accessed.

        The BlogObject is given a self.settings attribute in order to
        suppress unrelated to exceptions. (Subclasses are required to
        have self.settings.)
        """
        bo = majestic.BlogObject()

        settings = majestic.load_settings(
            files=[TEST_BLOG_DIR.joinpath('settings.json')], local=False)
        bo._settings = settings     # Suppress exceptions about settings

        for prop in ['url', 'output_path']:
            with self.assertRaises(NotImplementedError):
                getattr(bo, prop)

    def test_BlogObject_set_path_part(self):
        """Can override the path_part property by setting it

        Directly setting path_part makes it easier to directly
        override both the output_path and url properties, as
        they both retrieve the path part from that attribute.

        As path_part stores the constructed string at _path_part,
        users could override that but that should be an implementation
        detail.
        """
        bo = majestic.BlogObject()
        path_part = 'index.html'
        bo.path_part = path_part
        self.assertEqual(bo.path_part, path_part)

    def test_BlogObject_set_url(self):
        """Can override the url property by setting it

        This tests the url setter and ensures that BlogObject is
        actually setting and checking the underlying variable and
        not just raising NotImplementError regardless.
        """
        bo = majestic.BlogObject()
        url = 'http://example.com/my-test-url.html'
        bo.url = url
        self.assertEqual(bo.url, url)

    def test_BlogObject_url_trims_index(self):
        """URL property trims index.html from path_part

        This is necessary to have clean URLs internally if the path
        template writes the file as index.html in a subdirectory.
        """
        bo = majestic.BlogObject()
        base_url = 'http://example.com'
        self.settings['site']['url'] = base_url
        bo._settings = self.settings

        path_part = 'some_dir/index.html'
        bo.path_part = base_url + '/' + path_part
        self.assertEqual(bo.url, base_url + '/some_dir/')

    def test_BlogObject_set_output_path(self):
        """Can override the output_path property by setting it

        This tests the output_path setter and ensures that BlogObject
        is actually setting and checking the underlying variable and
        not just raising NotImplementError regardless.
        """
        bo = majestic.BlogObject()
        path = '/some/path/on/the/system'
        bo.output_path = path
        self.assertEqual(bo.output_path, path)

    def render_tests_setup_helper(self, test_file_name):
        """Return a properly overriden and set up BlogObject for file tests

        test_file_name serves as the name of the template file to load
        as well as the file in the test-output directory to write to.

        BlogObject has its key class variables, which would normally raise
        on instances, overriden to use this name, allowing the tests to
        proceed without having to use a concrete subclass.

        BlogObject by design cannot normally be written to a file. But to
        avoid having to test a concrete subclass, which may have its own
        problems, we monkey around with BlogObject to allow us to test it.
        """

        # Override BlogObject variables
        majestic.BlogObject._template_file_key = test_file_name
        bo = majestic.BlogObject()
        bo.path_part = test_file_name

        # Override settings
        self.settings['templates'][test_file_name] = test_file_name
        self.settings['paths'][test_file_name] = test_file_name
        bo._settings = self.settings

        return bo

    def render_tests_read_and_delete_file(self, filename):
        """Read and delete file 'name' in the test-output dir

        Teardown helper for render_to_disk tests.
        """
        file = self.test_output_dir.joinpath(filename)
        with file.open() as f:
            content = f.read()
        file.unlink()
        return content

    def test_BlogObject_render_basic(self):
        """render_to_disk chooses template and writes to correct location"""
        name = 'basic'
        bo = self.render_tests_setup_helper(name)

        bo.render_to_disk(self.env)

        self.assertEqual(self.render_tests_read_and_delete_file(name),
                         'This is the template for the basic test.')

    def test_BlogObject_render_kwargs(self):
        """render_to_disk passes keyword arguments to the render function"""
        name = 'kwargs'
        bo = self.render_tests_setup_helper(name)

        bo.render_to_disk(self.env,
                          some_kwarg='abc',
                          another_kwarg=[1, 2, 3])

        self.assertEqual(self.render_tests_read_and_delete_file(name),
                         'abc\n[1, 2, 3]')

    def test_BlogObject_render_self_passed_as_content(self):
        """render_to_disk passes self to render as the 'content' kwarg"""
        name = 'self-is-content'
        bo = self.render_tests_setup_helper(name)
        bo.some_attribute = 42

        bo.render_to_disk(self.env)

        self.assertEqual(self.render_tests_read_and_delete_file(name),
                         '42')


class TestRSSFeed(unittest.TestCase):
    """Test the RSSFeed class"""
    def setUp(self):
        settings_path = TEST_BLOG_DIR.joinpath('settings.json')
        self.settings = majestic.load_settings(files=[settings_path],
                                               local=False)
        self.number_of_posts = 5
        self.settings['rss']['number of posts'] = self.number_of_posts

        starting_date = datetime(2015, 9, 22, 19)
        self.posts = [
            majestic.Post(title='post {}'.format(i), body='Here’s some text!',
                          date=starting_date - timedelta(i),
                          settings=self.settings)
            for i in range(40)
            ]
        random.shuffle(self.posts)      # Ensure not sorted

    def test_RSSFeed_init_limit_posts(self):
        """RSSFeed sets self.posts to subset of posts arg on init

        The number of posts in RSSFeed.posts should equal self.number_of_posts.
        """
        feed = majestic.RSSFeed(posts=self.posts, settings=self.settings)
        self.assertEqual(len(feed.posts), self.number_of_posts)

    def test_RSSFeed_init_posts_sorted(self):
        """RSSFeed sets self.posts to sorted subset of posts arg on init

        RSSFeed.posts should be sorted by date, newest first.
        """
        feed = majestic.RSSFeed(posts=self.posts, settings=self.settings)
        sorted_posts = sorted(self.posts, reverse=True)[:self.number_of_posts]
        self.assertEqual(feed.posts, sorted_posts)

    def test_RSSFeed_sets_key_variables(self):
        """RSSFeed should set key variables required by BlogObject"""
        feed = majestic.RSSFeed(posts=self.posts, settings=self.settings)
        self.assertEqual(feed._path_template_key, 'rss path template')
        self.assertEqual(feed._template_file_key, 'rss')


class TestArchives(unittest.TestCase):
    """Test the Archives class"""
    def setUp(self):
        settings_path = TEST_BLOG_DIR.joinpath('settings.json')
        self.settings = majestic.load_settings(files=[settings_path],
                                               local=False)
        starting_date = datetime(2015, 9, 22, 19)
        self.posts = [
            majestic.Post(title='post {}'.format(i), body='Here’s some text!',
                          date=starting_date - timedelta(i),
                          settings=self.settings)
            for i in range(40)
            ]
        random.shuffle(self.posts)      # Ensure not sorted

    def test_Archives_init_posts_sorted(self):
        """Archives sorts posts before storing on self

        Archives.posts should be sorted by date, newest first.
        """
        arch = majestic.Archives(posts=self.posts, settings=self.settings)
        sorted_posts = sorted(self.posts, reverse=True)
        self.assertEqual(arch.posts, sorted_posts)

    def test_Archives_sets_key_variables(self):
        """Archives should set key variables required by BlogObject"""
        arch = majestic.Archives(posts=self.posts, settings=self.settings)
        self.assertEqual(arch._path_template_key, 'archives path template')
        self.assertEqual(arch._template_file_key, 'archives')


class TestPostsCollection(unittest.TestCase):
    """Test the PostsCollection base class

    Index, Archives and RSSFeed should inherit from this, and it should
    provide for storing settings and a list of posts on self.

    It should sort posts, newest-first.

    It should also implement __iter__ on behalf of its subclasses.
    """
    def setUp(self):
        settings_path = TEST_BLOG_DIR.joinpath('settings.json')
        self.settings = majestic.load_settings(files=[settings_path],
                                               local=False)
        starting_date = datetime(2015, 9, 22, 19)
        self.posts = [
            majestic.Post(title='post {}'.format(i), body='Here’s some text!',
                          date=starting_date - timedelta(i),
                          settings=self.settings)
            for i in range(40)
            ]
        random.shuffle(self.posts)      # Ensure not sorted

    def test_PostsCollection_store_posts(self):
        """PostsCollection stores a list of posts newest-first"""
        coll = majestic.PostsCollection(posts=self.posts,
                                        settings=self.settings)
        self.assertEqual(sorted(self.posts, reverse=True), coll.posts)

    def test_PostsCollection_iterator(self):
        """PostsCollection can be iterated over"""
        coll = majestic.PostsCollection(posts=self.posts,
                                        settings=self.settings)
        sorted_posts = sorted(self.posts, reverse=True)
        for idx, post in enumerate(coll):
            self.assertEqual(post, sorted_posts[idx])


class TestSitemap(unittest.TestCase):
    """Test the Sitemap class

    Sitemap takes a list of important locations (front page, pages, posts)
    and stores a list of tuples (url, output file modification time).

    The modification time is obtained by calling stat() on the output_path,
    so the Sitemap should be created after all the other files have been
    written out.
    """
    def setUp(self):
        settings_path = TEST_BLOG_DIR.joinpath('settings.json')
        self.settings = majestic.load_settings(files=[settings_path],
                                               local=False)
        self.output_dir = Path(self.settings['paths']['output root'])
        self.files = [
            majestic.Post(title='', slug='post', date=datetime(2015, 1, 1),
                          body='', settings=self.settings),
            majestic.Page(title='', slug='page', body='',
                          settings=self.settings),
            majestic.Index(posts=[], settings=self.settings, page_number=1),
        ]
        # Make dummy files and directories
        for f in self.files:
            try:
                f.output_path.parent.mkdir(parents=True)
            except FileExistsError:
                pass
            f.output_path.touch()

    def tearDown(self):
        """Clean up dummy files"""
        shutil.rmtree(str(self.output_dir))

    def test_Sitemap_sets_key_variables(self):
        """Sitemap should set key variables required by BlogObject"""
        sitemap = majestic.Sitemap(content=[], settings=self.settings)
        self.assertEqual(sitemap._path_template_key, 'sitemap path template')
        self.assertEqual(sitemap._template_file_key, 'sitemap')

    def test_Sitemap_sets_pairs(self):
        """Sitemap should store the url and output file mod date of content

        Sitemap is initialised with a list, content, of BlogObjects from
        which it should store the url and modification date of the file
        at output_path.

        The modification date should be an aware datetime in UTC.

        These should be stored at self.url_date_pairs.
        """
        expected = []
        for file in self.files:
            loc = file.url
            mtime = file.output_path.stat().st_mtime
            mod_date = datetime.fromtimestamp(mtime, tz=pytz.utc)
            expected.append((loc, mod_date))

        sitemap = majestic.Sitemap(content=self.files, settings=self.settings)
        self.assertEqual(expected, sitemap.url_date_pairs)

    def test_Sitemap_iter(self):
        """Iterating over Sitemap produces tuples of (str, datetime)"""
        sitemap = majestic.Sitemap(content=self.files, settings=self.settings)
        expected_types = [str, datetime]
        for item in sitemap:
            self.assertEqual(expected_types, [type(x) for x in item])


class TestFull(unittest.TestCase):
    """Test the processing of a full source directory

    Each test checks for the presence of certain files in certain
    locations in the output directory.
    """
    def setUp(self):
        self.blogdir = MAJESTIC_DIR.joinpath('test-full')
        self.outputdir = self.blogdir.joinpath('output')
        os.chdir(str(self.blogdir))
        self.settings = majestic.load_settings()
        self.expected = {
            '.': {
                'dirs': ['2012', '2013', '2014', '2015'],
                'posts': [],
                'pages': ['info.html'],
                'index': ['index.html',
                          'page-2.html',
                          'page-3.html'],
                'archives': ['archives.html'],
                'rss': ['rss.xml'],
                'sitemap': ['sitemap.xml']
                },
            './2012': {
                'dirs': ['07', '08', '12'],
                'posts': []
                },
            './2012/07': {
                'dirs': [],
                'posts': ['pelican-now-has-a-blog-of-its-own.html']
                },
            './2012/08': {
                'dirs': [],
                'posts': ['pelican-3-0-released.html']
                },
            './2012/12': {
                'dirs': [],
                'posts': ['pelican-3-1-released.html']
                },
            './2013': {
                'dirs': ['04', '07', '09'],
                'posts': []
                },
            './2013/04': {
                'dirs': [],
                'posts': ['pelican-3.2-released.html',
                          'pelicans-unified-codebase.html']
                },
            './2013/07': {
                'dirs': [],
                'posts': ['using-pelican-with-heroku.html']
                },
            './2013/09': {
                'dirs': [],
                'posts': ['pelican-3.3-released.html']
                },
            './2014': {
                'dirs': ['02', '07', '11'],
                'posts': []
                },
            './2014/02': {
                'dirs': [],
                'posts': ['i18n-subsites-plugin-released.html']
                },
            './2014/07': {
                'dirs': [],
                'posts': ['pelican-3.4-released.html']
                },
            './2014/11': {
                'dirs': [],
                'posts': ['pelican-3.5-released.html']
                },
            './2015': {
                'dirs': ['06'],
                'posts': []
                },
            './2015/06': {
                'dirs': [],
                'posts': ['pelican-3.6-released.html']
                },
            }

    def tearDown(self):
        """Clean up output files"""
        shutil.rmtree(str(self.outputdir))

    def test_process_blog_posts_only(self):
        """process_blog correctly writes out the posts"""
        majestic.process_blog(
            settings=self.settings, posts=True,
            pages=False, index=False, archives=False,
            rss=False, sitemap=False, extensions=False)
        os.chdir(str(self.outputdir))
        for dirpath, dirnames, filenames in os.walk('.'):
            self.assertTrue(dirpath in self.expected)
            self.assertEqual(
                set(self.expected[dirpath]['posts']),
                set(f for f in filenames if not f.startswith('.')))

    def test_process_blog_pages_only(self):
        """process_blog correctly writes out the pages"""
        majestic.process_blog(
            settings=self.settings, pages=True,
            posts=False, index=False, archives=False,
            rss=False, sitemap=False, extensions=False)
        os.chdir(str(self.outputdir))
        files_set = {p.name for p in Path().iterdir()
                     if p.is_file()
                     if not p.name.startswith('.')}
        self.assertEqual(set(self.expected['.']['pages']), files_set)

    def test_process_blog_indexes_only(self):
        """process_blog correctly writes out the indexes"""
        majestic.process_blog(
            settings=self.settings, index=True,
            posts=False, pages=False, archives=False,
            rss=False, sitemap=False, extensions=False)
        os.chdir(str(self.outputdir))
        files_set = {p.name for p in Path().iterdir()
                     if p.is_file()
                     if not p.name.startswith('.')}
        self.assertEqual(set(self.expected['.']['index']), files_set)

    def test_process_blog_archives_only(self):
        """process_blog correctly writes out the archives"""
        majestic.process_blog(
            settings=self.settings, archives=True,
            posts=False, pages=False, index=False,
            rss=False, sitemap=False, extensions=False)
        os.chdir(str(self.outputdir))
        files_set = {p.name for p in Path().iterdir()
                     if p.is_file()
                     if not p.name.startswith('.')}
        self.assertEqual(set(self.expected['.']['archives']), files_set)

    def test_process_blog_rss_only(self):
        """process_blog correctly writes out the rss feed"""
        majestic.process_blog(
            settings=self.settings, rss=True,
            posts=False, pages=False, index=False,
            archives=False, sitemap=False, extensions=False)
        os.chdir(str(self.outputdir))
        files_set = {p.name for p in Path().iterdir()
                     if p.is_file()
                     if not p.name.startswith('.')}
        self.assertEqual(set(self.expected['.']['rss']), files_set)

    def test_process_blog_all(self):
        """process_blog correctly writes out all expected files"""
        majestic.process_blog(settings=self.settings, extensions=False)
        os.chdir(str(self.outputdir))
        for dirpath, dirnames, filenames in os.walk('.'):
            self.assertTrue(dirpath in self.expected)
            self.assertEqual(
                set(self.expected[dirpath]['dirs']),
                set(dirnames))
            for content in ['posts', 'pages', 'index', 'archives',
                            'rss', 'sitemap']:
                if content in self.expected[dirpath]:
                    self.assertLessEqual(  # subset test
                        set(self.expected[dirpath][content]),
                        set(filenames))

    def test_process_blog_extensions_posts_and_pages(self):
        """process_blog invokes extensions for posts_and_pages

        The test extension adds an attribute test_attr to each of the
        posts and pages (set to 'post' and 'page' respectively), so
        we use a special template, called extension-test.html, that
        only includes the value of this attribute.

        It also adds a programmatically created page to objects_to_write.
        We test for this by checking the output path for the file, also
        named 'extension-test.html'.
        """
        self.settings['templates']['post'] = 'extension-test.html'
        self.settings['templates']['page'] = 'extension-test.html'
        majestic.process_blog(settings=self.settings, index=False,
                              archives=False, rss=False, sitemap=False)
        posts = self.outputdir.glob('20*/*/*.html')

        existing_page = self.outputdir.joinpath('info.html')
        new_page = self.outputdir.joinpath('extension-test.html')

        # Check programmatically created page was written
        self.assertTrue(new_page.exists())

        # Read files to check test_attr was set (and written with template)
        for post in posts:
            with post.open() as f:
                self.assertEqual(f.read().strip(), 'post')
        for page in [existing_page, new_page]:
            with page.open() as f:
                self.assertEqual(f.read().strip(), 'page')

    def test_process_blog_extensions_objects_to_write(self):
        """process_blog invokes extensions for objects_to_write

        The test extension adds a new page to the end of
        objects_to_write, named 'objects_to_write.html'.

        This should be written to disk.
        """
        majestic.process_blog(settings=self.settings, index=False,
                              archives=False, rss=False, sitemap=False)

        # Check programmatically created page was written
        new_page = self.outputdir.joinpath('objects_to_write.html')
        self.assertTrue(new_page.exists())

    def test_process_blog_only_write_new(self):
        """process_blog writes only Content considered new

        Content subclasses (Pages and Posts) should have their
        .is_new property checked before writing them out.

        This test only tests single Page for simplicity.
        """
        kwargs = dict(settings=self.settings, pages=True,
                      posts=False, index=False, archives=False,
                      rss=False, sitemap=False)
        majestic.process_blog(**kwargs)
        output = self.outputdir.joinpath(self.expected['.']['pages'][0])
        first_mtime = output.stat().st_mtime
        time.sleep(2)
        majestic.process_blog(**kwargs)
        second_mtime = output.stat().st_mtime
        self.assertEqual(first_mtime, second_mtime)

    def test_process_blog_force_write_all(self):
        """process_blog can be forced to write 'old' Content

        By default, Content subclasses have their .is_new property
        checked before writing them out. But this can be overridden
        by passing False for write_only_new in the process_blog call.

        This test only tests single Page for simplicity.
        """
        kwargs = dict(settings=self.settings, write_only_new=False,
                      pages=True, posts=False, index=False, archives=False,
                      rss=False, sitemap=False)
        majestic.process_blog(**kwargs)
        output = self.outputdir.joinpath(self.expected['.']['pages'][0])
        first_mtime = output.stat().st_mtime
        time.sleep(2)
        majestic.process_blog(**kwargs)
        second_mtime = output.stat().st_mtime
        self.assertNotEqual(first_mtime, second_mtime)


class TestExtensions(unittest.TestCase):
    """Test the mechanisms for loading and applying extensions"""
    def setUp(self):
        os.chdir(str(TEST_BLOG_DIR))
        self.settings = majestic.load_settings()
        ext_dir_name = self.settings['paths']['extensions root']
        self.ext_dir = TEST_BLOG_DIR.joinpath(ext_dir_name)
        self.posts = [majestic.Post(title='test', body='test',
                                    date=datetime.now(),
                                    settings=self.settings)]
        self.pages = [majestic.Page(title='test', body='test',
                                    settings=self.settings)]

    def test_load_extensions(self):
        """load_extensions returns expected extensions from directory"""
        expected_names = [fn.stem for fn in self.ext_dir.iterdir()
                          if fn.suffix == '.py']
        result = majestic.load_extensions(self.ext_dir)
        result_names = [m.__name__ for m in result]
        self.assertEqual(expected_names, result_names)

    def test_load_extensions_empty(self):
        """load_extensions returns empty list for directory with no modules"""
        with tempfile.TemporaryDirectory() as ext_dir:
            ext_dir_path = Path(ext_dir)
            result = majestic.load_extensions(ext_dir_path)
        self.assertFalse(result)

    def test_apply_extensions_posts_and_pages(self):
        """apply_extensions correctly processes posts and pages

        Returned dictionary should include the following keys:
            pages
            posts
            new_objects

        We use a dummy module, a, whose process method just adds
        an attribute, test_attr, to each post and page. Posts have
        test_attr set to 'post', pages have test_attr set to 'page'.

        apply_extensions should return a dictionary, storing the posts
        list under 'posts' and the pages list under 'pages', and extra
        objects to write under 'new_objects' (or an empty list).
        """
        extensions = majestic.load_extensions(self.ext_dir)

        result = majestic.apply_extensions(
            stage=majestic.ExtensionStage.posts_and_pages,
            modules=extensions, pages=self.pages,
            posts=self.posts, settings=self.settings)

        # Check new_objects is the empty list
        self.assertEqual(result['new_objects'], [])

        # Check test_attr is set properly on posts and pages
        for key in ('post', 'page'):
            self.assertEqual(result[key + 's'][0].test_attr, key)

    def test_apply_extensions_objects_to_write(self):
        """apply_extensions correctly processes objects_to_write

        Returned dictionary should include the following key:
            objects

        We use a dummy module, a, whose process method just adds
        an attribute, test_attr, to each object, set to 'obj'.

        apply_extensions should return a dictionary, storing the
        list of objects to write under 'objects'.
        """
        extensions = majestic.load_extensions(self.ext_dir)
        objs = self.posts + self.pages
        result = majestic.apply_extensions(
            stage=majestic.ExtensionStage.objects_to_write,
            modules=extensions, objects=objs,
            settings=self.settings)

        for obj in result['objects']:
            self.assertEqual(obj.test_attr, 'obj')

    def test_apply_extensions_posts_and_pages_keys(self):
        """Dictionary returned from apply_extensions contains correct keys

        For the posts_and_pages stage.

        While extensions don't have to include all the keys in the
        dictionary they return, apply_extensions should return a
        dictionary that always has all of the keys.
        """
        keys = {'posts', 'pages', 'new_objects'}
        result = majestic.apply_extensions(
            stage=majestic.ExtensionStage.posts_and_pages,
            modules=[], pages=[], posts=[],
            settings=self.settings)
        self.assertEqual(keys, set(result))

    def test_apply_extensions_objects_to_write_keys(self):
        """Dictionary returned from apply_extensions contains correct keys

        For the objects_to_write stage.

        If extensions implement process_objects_to_write, they should
        always return a dictionary with the objects list under the key
        objects.

        For consistency, apply_extensions should return a dictionary
        of the same form.
        """
        keys = {'objects'}
        result = majestic.apply_extensions(
            stage=majestic.ExtensionStage.objects_to_write,
            modules=[], objects=[], settings=self.settings)
        self.assertEqual(keys, set(result))


class TestCopyFiles(unittest.TestCase):
    """Test the file copying/symlinking features"""
    def setUp(self):
        os.chdir(str(MAJESTIC_DIR.joinpath('test-copy')))
        self.settings = majestic.load_settings()
        self.output_dir = Path(self.settings['paths']['output root'])

    def tearDown(self):
        try:
            shutil.rmtree(str(self.output_dir))
        except FileNotFoundError:
            pass

    def test_parse_copy_paths_simple(self):
        """parse_copy_paths produces list of src/dst pairs for simple list

        This test handles the most simple scenario: a list of paths to
        copy to the output directory with no new subdirectories or renames.
        """
        copy_paths = [
            ['404.html'],
            ['images']
            ]
        expected = [
            (Path('404.html'), self.output_dir.joinpath('404.html')),
            (Path('images'), self.output_dir.joinpath('images'))
            ]
        result = majestic.parse_copy_paths(path_list=copy_paths,
                                           output_root=self.output_dir)
        self.assertEqual(expected, result)

    def test_parse_copy_paths_glob(self):
        """parse_copy_paths produces list of src/dst pairs for glob path

        In this test, check that a glob path produces the expected list of
        src/dst pairs — importantly that one path rule can produce several
        such pairs.
        """
        copy_paths = [
            ['images/*.jpg']
            ]
        expected = [
            (Path('images/copytest1.jpg'),
             self.output_dir.joinpath('copytest1.jpg')),
            (Path('images/copytest2.jpg'),
             self.output_dir.joinpath('copytest2.jpg'))
            ]
        result = majestic.parse_copy_paths(path_list=copy_paths,
                                           output_root=self.output_dir)
        self.assertEqual(expected, result)

    def test_parse_copy_paths_subdir(self):
        """parse_copy_paths result includes specified subdir

        In this test, check that a path specifying a subdir produces a
        destination that includes the subdir.
        """
        copy_paths = [
            ['404.html', {'subdir': 'static'}],
            ['images', {'subdir': 'static'}]
            ]
        expected = [
            (Path('404.html'), self.output_dir.joinpath('static/404.html')),
            (Path('images'), self.output_dir.joinpath('static/images'))
            ]
        result = majestic.parse_copy_paths(path_list=copy_paths,
                                           output_root=self.output_dir)
        self.assertEqual(expected, result)

    def test_parse_copy_paths_name(self):
        """parse_copy_paths result includes specified new name

        In this test, check that a path specifying a name produces a
        destination whose last component is the new name.
        """
        copy_paths = [
            ['404.html', {'name': 'error.html'}],
            ['images', {'name': 'img'}]
            ]
        expected = [
            (Path('404.html'), self.output_dir.joinpath('error.html')),
            (Path('images'), self.output_dir.joinpath('img'))
            ]
        result = majestic.parse_copy_paths(path_list=copy_paths,
                                           output_root=self.output_dir)
        self.assertEqual(expected, result)

    def test_parse_copy_paths_subdir_and_name(self):
        """parse_copy_paths result includes specified subdir and name

        In this test, check that a path specifying both a subdir and
        a new name produces a destination which includes both
        """
        copy_paths = [
            ['404.html', {'subdir': 'static', 'name': 'error.html'}],
            ['images', {'subdir': 'static', 'name': 'img'}]
            ]
        expected = [
            (Path('404.html'), self.output_dir.joinpath('static/error.html')),
            (Path('images'), self.output_dir.joinpath('static/img'))
            ]
        result = majestic.parse_copy_paths(path_list=copy_paths,
                                           output_root=self.output_dir)
        self.assertEqual(expected, result)

    def test_mkdir_exist_ok(self):
        """mkdir_parents_ok ensures enclosing directory exists

        mkdir_exist_ok should make the target directory
        and suppress any FileExistsError if it already exists.
        """
        paths = [
            self.output_dir.joinpath('404.html'),
            self.output_dir.joinpath('images')
            ]
        for dest in paths:
            majestic.mkdir_exist_ok(dest)
            self.assertTrue(dest.parent.exists())

    def test_copy_files_simple(self):
        """copy_files copies sources to the specified output

        Both files and directories should be copied.

        copy_files should create enclosing folders as necessary.
        """
        paths = [
            [Path('404.html'), self.output_dir.joinpath('404.html')],
            [Path('404.html'), self.output_dir.joinpath('404.html')],
            [Path('images'), self.output_dir.joinpath('images')]
            ]
        majestic.copy_files(paths)
        for source, dest in paths:
            self.assertTrue(dest.exists())
            self.assertEqual(source.stat().st_size, dest.stat().st_size)

    def test_copy_files_dir_updated(self):
        """copy_files copies modified files inside target directory

        This tests whether copy_files checks the files inside the
        target directory for modifications rather than just testing
        the containing directory (which may not have its mtime
        changed by a modification to a file it contains).
        """
        src = Path('images')
        dst = self.output_dir.joinpath('images')
        paths = [[src, dst]]

        test_filename = 'copytest1.jpg'
        src_file = src.joinpath(test_filename)
        dst_file = dst.joinpath(test_filename)

        self.output_dir.mkdir()
        shutil.copytree(str(src), str(dst))     # Manually copy over directory

        old_dst_mtime = dst_file.stat().st_mtime
        self.assertEqual(src_file.stat().st_mtime, old_dst_mtime)

        time.sleep(1)   # Ensure m_time will be different
        src_file.touch()
        # Check src now has a different mtime
        self.assertNotEqual(src_file.stat().st_mtime, old_dst_mtime)

        majestic.copy_files(paths)
        new_dst_mtime = dst_file.stat().st_mtime
        # Check that modified source has indeed been copied
        self.assertNotEqual(old_dst_mtime, new_dst_mtime)

    def test_copy_files_dir_exists(self):
        """When copying dirs, copy_files should remove existing dest dir

        This is to avoid shutil.copytree raising FileExistsError.

        It's necessary to sleep for a second before touching the folder to
        ensure the modification date is properly changed, and ensure that
        copy_files doesn't skip the folder (making the test useless!).
        """
        src = Path('images')
        dst = self.output_dir.joinpath('images')
        paths = [[src, dst]]

        dst.mkdir(parents=True)  # Ensure destination dir exists
        time.sleep(1)            # Modification date resolution
        src.touch()              # Ensure src is newer (so should be copied)

        try:
            majestic.copy_files(paths)
        except FileExistsError:
            self.fail('destination directory was not removed')

    def test_link_files_simple(self):
        """link_files links to sources at the specified output locations

        Both files and directories should be linked.

        link_files should create enclosing folders as necessary.
        """
        paths = [
            [Path('404.html'), self.output_dir.joinpath('404.html')],
            [Path('404.html'), self.output_dir.joinpath('404.html')],
            [Path('images'), self.output_dir.joinpath('images')]
            ]
        majestic.link_files(paths)
        for source, dest in paths:
            self.assertTrue(dest.is_symlink())
            self.assertEqual(source.stat().st_size, dest.stat().st_size)

    def test_copy_resources(self):
        """copy_resources loads resources.json file and copies files"""
        expected_walk = [
            ('output', ['resources', 'static'], []),
            ('output/resources', ['img'], []),
            ('output/resources/img', [], ['copytest1.jpg', 'copytest2.jpg']),
            ('output/static', [], ['error.html']),
        ]
        majestic.copy_resources(settings=self.settings)
        self.assertEqual(sorted(expected_walk), sorted(os.walk('output')))

    def test_copy_resources_links(self):
        """copy_resources correctly uses symlinks when use_symlinks=True"""
        locations = [
            self.output_dir.joinpath('static', 'error.html'),
            self.output_dir.joinpath('resources', 'img'),
        ]

        majestic.copy_resources(settings=self.settings, use_symlinks=True)
        for loc in locations:
            self.assertTrue(loc.is_symlink())


if __name__ == '__main__':
    unittest.main()
