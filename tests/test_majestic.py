from datetime import datetime
import locale
import os
from pathlib import Path
import shutil
import string
import tempfile
import time
import unittest

import jinja2
import pytz

import majestic

TESTS_DIR = Path(__file__).resolve().parent
MAJESTIC_DIR = TESTS_DIR.parent.joinpath('majestic')
TEST_BLOG_DIR = TESTS_DIR.joinpath('test-blog')

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


class TestFull(unittest.TestCase):
    """Test the processing of a full source directory

    Each test checks for the presence of certain files in certain
    locations in the output directory.
    """
    def setUp(self):
        self.blogdir = TESTS_DIR.joinpath('test-full')
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
        os.chdir(str(TESTS_DIR.joinpath('test-copy')))
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
