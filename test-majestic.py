from datetime import datetime
import os
import pathlib
import pytz
import string
import tempfile
import unittest


import majestic

MAJESTIC_DIR = pathlib.Path(__file__).resolve().parent
TEST_BLOG_DIR = MAJESTIC_DIR.joinpath('test-blog')


class TestLoadSettings(unittest.TestCase):
    """Default and site-specific settings tests"""
    def setUp(self):
        os.chdir(str(MAJESTIC_DIR))

    def test_load_default_settings(self):
        """Config class contains setting set only in default .cfg file"""
        settings = majestic.load_settings(default=True, local=False)
        self.assertTrue(settings.getboolean('testing', 'default cfg loaded'))

    def test_load_specific_only(self):
        """When given filenames, load only those files"""
        test_settings_fn = str(TEST_BLOG_DIR.joinpath('settings.cfg'))
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
        test_files = list(map(pathlib.Path, test_files))
        returned_files = list(majestic.markdown_files(posts_dir))
        test_files.sort()
        returned_files.sort()
        self.assertEqual(test_files, returned_files)

    def test_markdown_files_empty_dir(self):
        """result is empty when given empty dir"""
        temp_dir = pathlib.Path(tempfile.mkdtemp())
        files = majestic.markdown_files(temp_dir)
        self.assertFalse(list(files))
        temp_dir.rmdir()

    def test_markdown_files_nonempty_dir_no_md(self):
        """result is empty when given nonempty dir containing no md files"""
        temp_dir = pathlib.Path(tempfile.mkdtemp())
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
        self.date = datetime(2015, 8, 22, 9, 46)
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
        settings_path = str(TEST_BLOG_DIR.joinpath('settings.cfg'))
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
        """Accessing content.url should raise NotImplementedError"""
        content = majestic.Content(title=self.title, body=self.body,
                                   settings=self.settings)
        with self.assertRaises(NotImplementedError):
            content.url

    def test_output_path_attribute_raises(self):
        """Accessing content.output_path should raise NotImplementedError"""
        content = majestic.Content(title=self.title, body=self.body,
                                   settings=self.settings)
        with self.assertRaises(NotImplementedError):
            content.output_path

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
        self.date = datetime(2015, 8, 22, 9, 46)
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
        settings_path = str(TEST_BLOG_DIR.joinpath('settings.cfg'))
        self.settings = majestic.load_settings(files=[settings_path],
                                               local=False)

    def test_page_inheritance(self):
        """Page instances are also an instance of Content"""
        page = majestic.Page(title=self.title, body=self.body,
                             settings=self.settings)
        self.assertTrue(isinstance(page, majestic.Content))

    def test_page_init_output_path_and_url(self):
        """Page sets output_path and url on initialisation

        Output path should be a pathlib.Path object, url a str
        """
        page = majestic.Page(title=self.title, body=self.body,
                             settings=self.settings, slug='abc')

        path_template = self.settings['paths']['page output']
        path = path_template.format(content=page)

        output_dir = self.settings['paths']['output root']
        site_url = self.settings['site']['url']

        expected_output = pathlib.Path(output_dir).joinpath(path)
        expected_url = site_url + '/' + path

        self.assertEqual(expected_output, page.output_path)
        self.assertEqual(expected_url, page.url)


@unittest.SkipTest
class TestParseFile(unittest.TestCase):
    """Test that parse_file correctly processes markdown pages and posts"""
    def setUp(self):
        settings_path = str(TEST_BLOG_DIR.joinpath('settings.cfg'))
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
        date_format = self.settings.get('dates', 'date format')

        for file in self.lib_posts:
            with file.open() as f:
                meta, body = f.read().split('\n\n', maxsplit=1)
            meta = [line.split(':', maxsplit=1) for line in meta.splitlines()]
            meta = {key.lower().strip(): value.strip() for key, value in meta}

            file_dict = meta
            file_dict['body'] = body.strip('\n')
            file_dict['source_path'] = file

            post = majestic.parse_file(file, settings=self.settings)
            post_dict = post.meta.copy()
            post_dict['title'] = post.title
            post_dict['slug'] = post.slug
            post_dict['date'] = post.date.strftime(date_format)
            post_dict['body'] = post.body
            post_dict['source_path'] = post.source_path

            self.assertEqual(file_dict, post_dict)

    def test_about_page(self):
        """Parsing basic page should work as with posts"""
        page = majestic.parse_file(self.pages_path.joinpath('about.md'),
                                   settings=self.settings)
        self.assertEqual(page.title, 'About majestic')
        self.assertEqual(page.slug, 'about')
        self.assertEqual(
            page.body,
            ('Majestic makes websites out of markdown files.\n\n'
             'It is written in Python and was started by Rob Wells.'))

    def test_parse_known_bad_slug(self):
        """parse_file detects and normalises invalid slugs

        When given a file containing an invalid value for the slug,
        parse_file should return a content object where the slug
        has been normalised.

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
        known_bad_file = self.posts_path.joinpath('test_invalid_slug.md')
        good_chars = set(string.ascii_lowercase + string.digits + '-')

        post = majestic.parse_file(known_bad_file, settings=self.settings)
        self.assertLess(set(post.slug), good_chars)  # Subset test

    def test_parse_bad_percent_encoding(self):
        """parse_file normalises slugs containing invalid percent encoding"""
        bad_percent_file = self.posts_path.joinpath('test_bad_percent.md')
        bad_percent_slug = 'this-is-not-100%-valid'
        post = majestic.parse_file(bad_percent_file, settings=self.settings)
        self.assertNotEqual(post.slug, bad_percent_slug)

    def test_parse_known_good_slug(self):
        """parse_file does not normalise known good slug"""
        known_good_file = self.posts_path.joinpath('test_good_slug.md')
        known_good_slug = 'valid%20slug'

        post = majestic.parse_file(known_good_file, settings=self.settings)
        self.assertTrue(post.slug, known_good_slug)

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

    def test_draft_future_date(self):
        """parse_file returns None given a file with a future date"""
        result = majestic.parse_file(
            file=self.posts_path.joinpath('test_future_date.md'),
            settings=self.settings)
        self.assertIsNone(result)

    def test_explicit_draft(self):
        """parse_file returns None given a file with 'draft' in meta

        'draft' should appear (without quotes) at the end on a line by itself
        """
        result = majestic.parse_file(
            file=self.posts_path.joinpath('test_explicit_draft.md'),
            settings=self.settings)
        self.assertIsNone(result)

    def test_date_has_timezone(self):
        """parse_file correctly localizes the file's date"""
        result = majestic.parse_file(
            file=self.posts_path.joinpath('1979-07-19 Liberation Day.mkdown'),
            settings=self.settings)
        self.assertEqual(
            result.date.tzinfo,
            pytz.timezone(self.settings['dates']['timezone']))


if __name__ == '__main__':
    unittest.main()
