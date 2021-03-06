import unittest
import majestic
from majestic.content import (
    BlogObject, Content, Page, Post, ModificationDateError
    )
from majestic.utils import markdown_files

from datetime import datetime
import os
from pathlib import Path
import string
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
        returned_files = list(markdown_files(posts_dir))
        test_files.sort()
        returned_files.sort()
        self.assertEqual(test_files, returned_files)

    def test_markdown_files_empty_dir(self):
        """result is empty when given empty dir"""
        temp_dir = Path(tempfile.mkdtemp())
        files = markdown_files(temp_dir)
        self.assertFalse(list(files))
        temp_dir.rmdir()

    def test_markdown_files_nonempty_dir_no_md(self):
        """result is empty when given nonempty dir containing no md files"""
        temp_dir = Path(tempfile.mkdtemp())
        for x in range(20):
            temp_dir.touch(x)
        files = markdown_files(temp_dir)
        self.assertFalse(list(files))
        for file in temp_dir.iterdir():
            file.unlink()
        temp_dir.rmdir()


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

        self.test_output_dir = TESTS_DIR.joinpath('output-root')
        self.settings['paths']['output root'] = str(self.test_output_dir)

        self.templates_root = TESTS_DIR.joinpath('test-templates')
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
        self.assertIsInstance(BlogObject(), BlogObject)

    def test_BlogObject_properties_exist(self):
        """BlogObject defines expected properties and methods

        Expected:
            * path_part
            * output_path
            * url
            * render_to_disk
        """
        attrs = ['path_part', 'output_path', 'url', 'render_to_disk']
        bo = BlogObject()
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
        bo = BlogObject()
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
        bo = BlogObject()

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
        bo = BlogObject()
        path_part = 'index.html'
        bo.path_part = path_part
        self.assertEqual(bo.path_part, path_part)

    def test_BlogObject_set_url(self):
        """Can override the url property by setting it

        This tests the url setter and ensures that BlogObject is
        actually setting and checking the underlying variable and
        not just raising NotImplementError regardless.
        """
        bo = BlogObject()
        url = 'http://example.com/my-test-url.html'
        bo.url = url
        self.assertEqual(bo.url, url)

    def test_BlogObject_url_trims_index(self):
        """URL property trims index.html from path_part

        This is necessary to have clean URLs internally if the path
        template writes the file as index.html in a subdirectory.
        """
        bo = BlogObject()
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
        bo = BlogObject()
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
        class test_BlogObject(BlogObject):
            pass
        test_BlogObject._template_file_key = test_file_name
        bo = test_BlogObject()
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
        content = Content(title=self.title, body=self.body,
                          settings=self.settings)
        self.assertEqual([self.title, self.body, self.settings],
                         [content.title, content.body, content._settings])

    def test_content_init_meta(self):
        """Content stores extra kwargs as the .meta attribute"""
        content = Content(title=self.title, body=self.body,
                          settings=self.settings, foo='bar')
        self.assertEqual(content.meta['foo'], 'bar')

    def test_content_init_slug(self):
        """Content stores a valid slug as the slug attribute

        Slug validity is defined elsewhere, but this test uses the
        simplest possible slug, a single alphabetical character.
        """
        content = Content(title=self.title, body=self.body,
                          slug='a', settings=self.settings)
        self.assertEqual(content.slug, 'a')

    def test_content_init_slug_from_title(self):
        """Content creates a slug from the title one is not given

        Slug validity is defined elsewhere, but this test uses the
        simplest possible title for the source, a single alphabetical
        character.
        """
        content = Content(title='a', body=self.body,
                          settings=self.settings)
        self.assertEqual(content.slug, 'a')

    def test_content_init_invalid_slug(self):
        """Content normalises invalid slugs before storing them"""
        invalid_slug = '!not:valid!'
        expected = 'not-valid'
        content = Content(title='a', body=self.body,
                          settings=self.settings, slug=invalid_slug)
        self.assertEqual(content.slug, expected)

    def test_content_init_modification_date(self):
        """Content sets init arg modification_date as an attribute"""
        mod_date = datetime(2015, 1, 25, 9, 30)
        content = Content(title=self.title, body=self.body,
                          slug=self.slug, settings=self.settings,
                          modification_date=mod_date)
        self.assertEqual(content.modification_date, mod_date)

    def test_content_init_mod_date_from_source_path(self):
        """Content sets modification date from source file (if provided)"""
        expected_mod_date = datetime.fromtimestamp(
            self.middle_file.stat().st_mtime)
        content = Content(title=self.title, body=self.body,
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
        content = Content(title=self.title, body=self.body,
                          settings=self.settings, save_as=custom_path)
        self.assertEqual(content.path_part, custom_path)

    def test_content_is_new_no_output_file(self):
        """Content.is_new is True when no corresponding output file exists

        If there is no output file the content object is always considered
        new, even if it doesn't have a source file and wasn't created with
        an explicit modification date (ie programmatically).
        """
        content = Content(title=self.title, body=self.body,
                          slug=self.slug, settings=self.settings)
        # Override output path to ensure file does not exist
        content.output_path = Path('/tmp/test-majestic-no-file-here')
        self.assertTrue(content.is_new)

    def test_content_is_new_true_with_output_file(self):
        """Content.is_new is True when an older output file exists"""
        content = Content(title=self.title, body=self.body,
                          slug=self.slug, settings=self.settings,
                          source_path=self.newest_file)
        # Override output path
        content.output_path = self.oldest_file
        self.assertTrue(content.is_new)

    def test_content_is_new_false_with_output_file(self):
        """Content.is_new is False when a newer output file exists"""
        content = Content(title=self.title, body=self.body,
                          slug=self.slug, settings=self.settings,
                          source_path=self.oldest_file)
        # Override output path
        content.output_path = self.newest_file
        self.assertFalse(content.is_new)

    def test_content_is_new_raises(self):
        """Content.is_new raises if mod date is None and output file exists"""
        content = Content(title=self.title, body=self.body,
                          slug=self.slug, settings=self.settings)
        content.output_path = self.newest_file
        with self.assertRaises(ModificationDateError):
            content.is_new

    def test_content_is_new_setter(self):
        """Content.is_new is a property that can be set"""
        content = Content(title=self.title, body=self.body,
                          slug=self.slug, settings=self.settings)
        content.is_new = True
        self.assertTrue(content.is_new)

    def test_content_lt_title(self):
        """Content with different titles compare properly"""
        post_1 = Content(title='title a',
                         slug=self.slug, body=self.body,
                         settings=self.settings)
        post_2 = Content(title='title b',
                         slug=self.slug, body=self.body,
                         settings=self.settings)
        self.assertTrue(post_1 < post_2)
        self.assertFalse(post_2 < post_1)

    def test_content_compare_title_case_insensitive(self):
        """Content with titles that differ in case compare properly"""
        post_1 = Content(title='title a',
                         slug=self.slug, body=self.body,
                         settings=self.settings)
        post_2 = Content(title='title B',
                         slug=self.slug, body=self.body,
                         settings=self.settings)
        self.assertTrue(post_1 < post_2)

    def test_content_lt_slug(self):
        """Content with different slugs compare properly"""
        post_1 = Content(title=self.title,
                         slug='test-a', body=self.body,
                         settings=self.settings)
        post_2 = Content(title=self.title,
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
        page = Page(title=self.title, body=self.body,
                    settings=self.settings)
        self.assertTrue(isinstance(page, Content))

    def test_page_output_path_and_url(self):
        """Page defines output_path and url properties

        Output path should be a pathlib.Path object, url a str
        """
        page = Page(title=self.title, body=self.body,
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
        page = Page(title=self.title, body=self.body,
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
        page_a = Page(title=self.title, body=self.body,
                      settings=self.settings)
        page_b = Page(title=self.title, body=self.body,
                      settings=self.settings)
        page_c = Page(title='different', body=self.body,
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
        post = Post(title=self.title, body=self.body,
                    date=self.naive_date, settings=self.settings)
        self.assertTrue(isinstance(post, Content))

    def test_post_init_date(self):
        """Post stores provided date as self.date"""
        post = Post(title=self.title, body=self.body,
                    date=self.naive_date, settings=self.settings)
        self.assertEqual(self.aware_date, post.date)

    def test_post_init_date_string(self):
        """If given a str for date, Post parses it into a datetime object"""
        self.settings['dates']['format'] = '%Y-%m-%d %H:%M'
        post = Post(title=self.title, body=self.body,
                    date=self.date_string, settings=self.settings)
        self.assertEqual(self.aware_date, post.date)

    def test_date_has_timezone(self):
        """Post correctly localizes the provided date"""
        post = Post(title=self.title, body=self.body,
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
        post_a = Post(title=self.title, body=self.body,
                      settings=self.settings, date=self.naive_date)
        post_b = Post(title=self.title, body=self.body,
                      settings=self.settings, date=self.naive_date)
        post_c = Post(title=self.title, body=self.body,
                      settings=self.settings,
                      date=datetime(2015, 1, 1))
        self.assertEqual(post_a, post_b)
        self.assertNotEqual(post_a, post_c)

    def test_post_compare_lt_dates(self):
        """Posts with different dates compare properly"""
        post_1 = Post(title=self.title, body=self.body,
                      settings=self.settings,
                      date=datetime(2015, 1, 1))
        post_2 = Post(title=self.title, body=self.body,
                      settings=self.settings,
                      date=datetime(2014, 1, 1))
        self.assertLess(post_2, post_1)

    def test_post_compare_lt_identical_dates(self):
        """Posts with the same date but different titles compare properly

        The Post class should only test the dates, and delegate title and
        slug comparison to its superclass.
        """
        post_1 = Post(title='title a', body=self.body,
                      date=self.naive_date, settings=self.settings)
        post_2 = Post(title='title B', body=self.body,
                      date=self.naive_date, settings=self.settings)
        self.assertLess(post_1, post_2)

    def test_post_future_date_raises_DraftPost(self):
        """Initialising a Post with a future date raises DraftError"""
        with self.assertRaises(majestic.DraftError):
            Post(title=self.title, body=self.body,
                 settings=self.settings,
                 date=datetime(2100, 1, 1))

    def test_post_output_path_and_url(self):
        """Post defines output_path and url properties

        Output path should be a pathlib.Path object, url a str
        """
        post = Post(title=self.title, body=self.body,
                    settings=self.settings, date=self.naive_date)

        path_template = self.settings['paths']['post path template']
        path = path_template.format(content=post)

        output_dir = self.settings['paths']['output root']
        site_url = self.settings['site']['url']

        expected_output = Path(output_dir, path)
        expected_url = site_url + '/' + path

        self.assertEqual(expected_output, post.output_path)
        self.assertEqual(expected_url, post.url)


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

            post = Post.from_file(file, settings=self.settings)
            post_dict = post.meta.copy()
            post_dict['title'] = post.title
            post_dict['slug'] = post.slug
            post_dict['date'] = post.date.strftime(date_format)
            post_dict['body'] = post.body
            post_dict['source_path'] = post.source_path

            self.assertEqual(file_dict, post_dict)

    def test_about_page(self):
        """Parsing basic page should work as with posts"""
        page = Page.from_file(self.pages_path.joinpath('about.md'),
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

        post = Post.from_file(known_bad_file, settings=self.settings)
        self.assertLess(set(post.slug), good_chars)  # Subset test

    def test_parse_bad_percent_encoding(self):
        """.from_file normalises slugs containing invalid percent encoding"""
        bad_percent_file = self.posts_path.joinpath('test_bad_percent.md')
        bad_percent_slug = 'this-is-not-100%-valid'
        post = Post.from_file(bad_percent_file,
                              settings=self.settings)
        self.assertNotEqual(post.slug, bad_percent_slug)

    def test_parse_known_good_slug(self):
        """.from_file does not normalise known good slug"""
        known_good_file = self.posts_path.joinpath('test_good_slug.md')
        known_good_slug = 'valid%20slug'

        post = Post.from_file(known_good_file, settings=self.settings)
        self.assertTrue(post.slug, known_good_slug)

    def test_explicit_draft(self):
        """.from_file raises DraftError given a file with 'draft' in meta

        'draft' should appear (without quotes) on a line by itself
        """
        with self.assertRaises(majestic.DraftError):
            Post.from_file(
                file=self.posts_path.joinpath('test_explicit_draft.md'),
                settings=self.settings)
