from datetime import datetime, timedelta
import json
import os
from pathlib import Path
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
                         [content.title, content.body, content.settings])

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

    def test_url_property_raises(self):
        """Accessing content.url should raise NotImplementedError

        This is now achieved through calling .path_part, which raises
        """
        content = majestic.Content(title=self.title, body=self.body,
                                   settings=self.settings)
        with self.assertRaises(NotImplementedError):
            content.url

    def test_output_path_attribute_raises(self):
        """Accessing content.output_path should raise NotImplementedError

        This is now achieved through calling .path_part, which raises
        """
        content = majestic.Content(title=self.title, body=self.body,
                                   settings=self.settings)
        with self.assertRaises(NotImplementedError):
            content.output_path

    def test_set_url(self):
        """Can override the url property by setting it"""
        content = majestic.Content(title=self.title, body=self.body,
                                   settings=self.settings)
        url = 'http://example.com/my-test-url.html'
        content.url = url
        self.assertEqual(content.url, url)

    def test_set_output_path(self):
        """Can override the output_path property by setting it"""
        content = majestic.Content(title=self.title, body=self.body,
                                   settings=self.settings)
        path = '/some/path/on/the/system'
        content.output_path = path
        self.assertEqual(content.output_path, path)

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
        """_path_part correctly formats and stores Page's path part

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
        self.assertEqual(path, page._path_part)

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
        loader = jinja2.FileSystemLoader(
            self.settings['paths']['templates root'])
        self.jinja_env = jinja2.Environment(loader=loader)

    def test_jinja_environment_basic(self):
        """jinja_environment returns Environment with expected templates"""
        env = majestic.jinja_environment(
            templates_dir=self.settings['paths']['templates root'],
            settings=self.settings)
        self.assertEqual(self.jinja_env.list_templates(), env.list_templates())

    def test_jinja_environment_defaults(self):
        """jinja_environment results contains expected default options

        In particular:
            environment.auto_reload should be False
            environment.globals should contain 'settings'
        """
        env = majestic.jinja_environment(
            templates_dir=self.settings['paths']['templates root'],
            settings=self.settings)
        self.assertFalse(env.auto_reload)
        self.assertTrue('settings' in env.globals)

    def test_jinja_environment_custom_options(self):
        """jinja_environment properly applies custom jinja options"""
        opts = {'trim_blocks': True}
        env = majestic.jinja_environment(
            templates_dir=self.settings['paths']['templates root'],
            settings=self.settings,
            jinja_options=opts)
        self.assertTrue(env.trim_blocks)

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
            templates_dir=self.settings['paths']['templates root'],
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
        path_template = 'page-{index.page_number}.html'
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
        """paginate_index's result on known date gives expected result"""
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


if __name__ == '__main__':
    unittest.main()
