import unittest
import majestic

from datetime import datetime
import os
from pathlib import Path
import tempfile
import time

import pytz


TESTS_DIR = Path(__file__).resolve().parent
TEST_BLOG_DIR = TESTS_DIR.joinpath('test-blog')


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
