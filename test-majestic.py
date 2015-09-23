from datetime import datetime, timedelta
import json
import locale
import os
from pathlib import Path
import random
import string
import tempfile
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
        """Config class contains setting set only in default .cfg file"""
        settings = majestic.load_settings(default=True, local=False)
        self.assertTrue(settings.getboolean('testing', 'default cfg loaded'))

    def test_load_specific_only_str(self):
        """When given filenames (as str), load only those files"""
        test_settings_fn = str(TEST_BLOG_DIR.joinpath('settings.cfg'))
        settings = majestic.load_settings(default=False, local=False,
                                          files=[test_settings_fn])
        self.assertTrue(settings.getboolean('testing', 'test-blog cfg loaded'))

    def test_load_specific_only_Path(self):
        """When given filenames (as pathlib.Path), load only those files

        Tests that load_settings correctly handles paths given as
        pathlib.Path instead of str (as os functions expect).
        The burden of conversion should fall on the function
        itself, not its callers.
        """
        test_settings_fn = TEST_BLOG_DIR.joinpath('settings.cfg')
        settings = majestic.load_settings(default=False, local=False,
                                          files=[test_settings_fn])
        self.assertTrue(settings.getboolean('testing', 'test-blog cfg loaded'))

    def test_load_default_and_local(self):
        """Properly load defaults and settings.cfg in current directory"""
        os.chdir(str(TEST_BLOG_DIR))
        settings = majestic.load_settings(default=True, local=True)
        self.assertTrue(settings.getboolean('testing', 'test-blog cfg loaded'))
        self.assertTrue(settings.getboolean('testing', 'default cfg loaded'))

    def test_defaults_overriden_by_local(self):
        """Config files loaded in order so that locals override defaults"""
        default_settings = majestic.load_settings(default=True, local=False)
        overridden_value = default_settings.getboolean('testing',
                                                       'overridden setting')
        self.assertFalse(overridden_value)
        os.chdir(str(TEST_BLOG_DIR))
        combined_settings = majestic.load_settings()
        overridden_value = combined_settings.getboolean('testing',
                                                        'overridden setting')
        self.assertTrue(overridden_value)

    def test_settings_empty_when_not_given_anything(self):
        """Returned config object should be empty when everything disabled"""
        settings = majestic.load_settings(default=False, local=False)
        self.assertEqual(1, len(settings))
        self.assertFalse(list(settings['DEFAULT']))


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
        settings_path = TEST_BLOG_DIR.joinpath('settings.cfg')
        self.settings = majestic.load_settings(files=[settings_path],
                                               local=False)

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

        self.settings['markdown']['extensions'] = ''
        content = majestic.Content(title=self.title, settings=self.settings,
                                   body=original)
        self.assertEqual(plain_html, content.html)

        self.settings['markdown']['extensions'] = 'smarty'
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
        settings_path = TEST_BLOG_DIR.joinpath('settings.cfg')
        self.settings = majestic.load_settings(files=[settings_path],
                                               local=False)

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

        expected_output = Path(output_dir).joinpath(path)
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
        settings_path = TEST_BLOG_DIR.joinpath('settings.cfg')
        self.settings = majestic.load_settings(files=[settings_path],
                                               local=False)

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

        expected_output = Path(output_dir).joinpath(path)
        expected_url = site_url + '/' + path

        self.assertEqual(expected_output, post.output_path)
        self.assertEqual(expected_url, post.url)


class TestSlugFunctions(unittest.TestCase):
    """Test validate_slug and normalise_slug

    Slugs containing the following characters are deemed to be
    invalid (note the quoted space at the beginning):

    " " : / ? # [ ] @ ! $ & ' ( ) * + , ; =

    Slugs containing a percent character that is not followed by
    two hex digits are also deemed to be invalid.

    A normalised slug contains only the following characters:

    a-z 0-9 -

    A file's slug *is not* checked against the normalised characters.
    It is only normalised if it contains one of the reserved
    characters.

    The validator is liberal and the normaliser conservative. These
    characters are not reserved in a URI (and so pass the validator)
    but are not kept by the normaliser:

    . _ ~

    The normaliser also removes percent-encoded characters (%20).

    Reserved and unreserved character are adapted from
    IETF RFC 3986, Uniform Resource Identifier (URI): Generic Syntax
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


class TestFromFile(unittest.TestCase):
    """Test that .from_file on Content classes correctly parses files"""
    def setUp(self):
        settings_path = TEST_BLOG_DIR.joinpath('settings.cfg')
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
        settings_path = TEST_BLOG_DIR.joinpath('settings.cfg')
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
        opts = {'trim_blocks': True}
        env = majestic.jinja_environment(
            user_templates=self.settings['paths']['templates root'],
            settings=self.settings,
            jinja_options=opts)
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

    def test_load_jinja_options(self):
        """load_jinja_options parses the jinja.json file and returns a dict

        It should create the path to jinja.json from the templates root
        in the settings object.
        """
        templates_root = Path(self.settings['paths']['templates root'])
        json_file = templates_root.joinpath('jinja.json')
        with json_file.open() as f:
            expected = json.load(f)
        result = majestic.load_jinja_options(self.settings)
        self.assertEqual(expected, result)

    def test_jinja_environment_rfc822_filter(self):
        """jinja_environment adds rfc822_date as a custom filter"""
        env = majestic.jinja_environment(
            user_templates=self.settings['paths']['templates root'],
            settings=self.settings)
        self.assertEqual(env.filters['rfc822_date'], majestic.rfc822_date)


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
        settings_path = TEST_BLOG_DIR.joinpath('settings.cfg')
        self.settings = majestic.load_settings(files=[settings_path],
                                               local=False)
        self.settings['index']['posts per page'] = '2'
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
        """Index properly sets output path"""
        dummy_url = 'http://example.com'
        self.settings['site']['url'] = dummy_url
        indexes = [
            majestic.Index(page_number=n, settings=self.settings, posts=[])
            for n in range(1, 3)
            ]
        self.assertEqual(dummy_url, indexes[0].url)
        self.assertEqual(dummy_url + '/page-2.html', indexes[1].url)

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
        output_root = Path(self.settings['paths']['output root'])
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
            settings=None)  # Not needed

    def test_BlogObject_no_arguments(self):
        """BlogObject should not require arguments to init

        The intention is that BlogObject only contains default method
        implementations to be inherited and has no content of its own.
        """
        bo = majestic.BlogObject()      # This should not raise

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
            files=[TEST_BLOG_DIR.joinpath('settings.cfg')], local=False)
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
        settings_path = TEST_BLOG_DIR.joinpath('settings.cfg')
        self.settings = majestic.load_settings(files=[settings_path],
                                               local=False)
        self.number_of_posts = 5
        self.settings['rss']['number of posts'] = str(self.number_of_posts)

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
        settings_path = TEST_BLOG_DIR.joinpath('settings.cfg')
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


if __name__ == '__main__':
    unittest.main()
