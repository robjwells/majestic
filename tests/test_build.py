import os
from pathlib import Path
import shutil
import time
import unittest

import majestic


TESTS_DIR = Path(__file__).resolve().parent


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
            feeds=False, sitemap=False, extensions=False)
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
            feeds=False, sitemap=False, extensions=False)
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
            feeds=False, sitemap=False, extensions=False)
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
            feeds=False, sitemap=False, extensions=False)
        os.chdir(str(self.outputdir))
        files_set = {p.name for p in Path().iterdir()
                     if p.is_file()
                     if not p.name.startswith('.')}
        self.assertEqual(set(self.expected['.']['archives']), files_set)

    def test_process_blog_rss_only(self):
        """process_blog correctly writes out the rss feed"""
        majestic.process_blog(
            settings=self.settings, feeds=True,
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
                              archives=False, feeds=False, sitemap=False)
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
                              archives=False, feeds=False, sitemap=False)

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
                      feeds=False, sitemap=False)
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
                      feeds=False, sitemap=False)
        majestic.process_blog(**kwargs)
        output = self.outputdir.joinpath(self.expected['.']['pages'][0])
        first_mtime = output.stat().st_mtime
        time.sleep(2)
        majestic.process_blog(**kwargs)
        second_mtime = output.stat().st_mtime
        self.assertNotEqual(first_mtime, second_mtime)
