import unittest
from majestic import load_settings
from majestic.content import Post, Page
from majestic.collections import (
    PostsCollection, Archives, Index, RSSFeed, JSONFeed, Sitemap
    )
from majestic.utils import absolute_urls

from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import random
import shutil
from urllib.parse import urljoin

import pytz


TESTS_DIR = Path(__file__).resolve().parent
TEST_BLOG_DIR = TESTS_DIR.joinpath('test-blog')


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
        self.settings = load_settings(files=[settings_path],
                                      local=False)
        self.settings['index']['posts per page'] = 2
        path_template = 'page-{content.page_number}.html'
        self.settings['paths']['index pages path template'] = path_template
        self.settings['site']['url'] = 'http://example.com'

        dates = [datetime(2015, 1, 1) + timedelta(i) for i in range(5)]
        titles = ['A', 'B', 'C', 'D', 'E']
        bodies = ['A', 'B', 'C', 'D', 'E']
        self.posts = [
            Post(title=t, body=b, date=d, settings=self.settings)
            for t, b, d in zip(titles, bodies, dates)
            ]

    def test_Index_paginate_posts_per_index(self):
        """paginate_posts gives each Index the right number of posts"""
        result = Index.paginate_posts(posts=self.posts,
                                      settings=self.settings)
        for expected_count, index in zip([2, 2, 1], result):
            self.assertEqual(expected_count, len(index.posts))

    def test_Index_paginate_order(self):
        """paginate_posts returns Index objects ordered first to last"""
        result = Index.paginate_posts(posts=self.posts,
                                      settings=self.settings)
        for expected_number, index in enumerate(result, start=1):
            self.assertEqual(expected_number, index.page_number)

    def test_Index_attrs(self):
        """Each Index returned by paginate_posts has the correct attributes"""
        attr_list = ['page_number', 'newer_index_url', 'older_index_url',
                     'output_path', 'url', 'posts']
        result = Index.paginate_posts(posts=self.posts,
                                      settings=self.settings)
        for index in result:
            for attribute in attr_list:
                self.assertTrue(hasattr(index, attribute))

    def test_Index_output_path(self):
        """Index properly sets output path"""
        self.settings['paths']['output root'] = ''
        indexes = [
            Index(page_number=n, settings=self.settings, posts=[])
            for n in range(1, 3)
            ]
        self.assertEqual(Path('index.html'), indexes[0].output_path)
        self.assertEqual(Path('page-2.html'), indexes[1].output_path)

    def test_Index_url(self):
        """Index properly sets URL"""
        base_url = 'http://example.com'
        self.settings['site']['url'] = base_url
        indexes = [
            Index(page_number=n, settings=self.settings, posts=[])
            for n in range(1, 3)
            ]
        self.assertEqual(base_url, indexes[0].url)
        self.assertEqual(base_url + '/page-2.html', indexes[1].url)

    def test_Index_compare(self):
        """Index objects compare by page number"""
        index_a = Index(page_number=1, settings=self.settings, posts=[])
        index_b = Index(page_number=2, settings=self.settings, posts=[])
        self.assertLess(index_a, index_b)

    def test_Index_posts_sorted(self):
        """Index sorts posts by newest before storing them"""
        index = Index(page_number=1, settings=self.settings,
                      posts=self.posts)
        self.assertEqual(sorted(self.posts, reverse=True), index.posts)

    def test_Index_eq(self):
        """Two distinct Index objects with same attrs compare equal"""
        index_a = Index(page_number=1, settings=self.settings,
                        posts=self.posts)
        index_b = Index(page_number=1, settings=self.settings,
                        posts=self.posts)
        index_c = Index(page_number=2, settings=self.settings,
                        posts=self.posts)
        self.assertEqual(index_a, index_b)
        self.assertNotEqual(index_a, index_c)

    def test_Index_iter(self):
        """Index should support iteration over its posts

        Looping over an Index should be equivalent to looping
        its posts list attribute.
        """
        expected = sorted(self.posts, reverse=True)
        index = Index(page_number=1, settings=self.settings,
                      posts=self.posts)
        self.assertEqual(expected, [p for p in index])

    def test_Index_paginate_posts_result(self):
        """Result of paginate_posts on known date gives expected result"""
        expected = [
            Index(page_number=1, settings=self.settings,
                  posts=self.posts[-2:]),
            Index(page_number=2, settings=self.settings,
                  posts=self.posts[-4:-2]),
            Index(page_number=3, settings=self.settings,
                  posts=self.posts[:-4])
            ]

        expected[0].older_index_url = expected[1].url
        expected[1].older_index_url = expected[2].url
        expected[2].newer_index_url = expected[1].url
        expected[1].newer_index_url = expected[0].url

        result = Index.paginate_posts(
            posts=self.posts, settings=self.settings)
        self.assertEqual(expected, result)


class TestArchives(unittest.TestCase):
    """Test the Archives class"""
    def setUp(self):
        settings_path = TEST_BLOG_DIR.joinpath('settings.json')
        self.settings = load_settings(files=[settings_path],
                                      local=False)
        starting_date = datetime(2015, 9, 22, 19)
        self.posts = [
            Post(title='post {}'.format(i), body='Here’s some text!',
                 date=starting_date - timedelta(i),
                 settings=self.settings)
            for i in range(40)
            ]
        random.shuffle(self.posts)      # Ensure not sorted

    def test_Archives_init_posts_sorted(self):
        """Archives sorts posts before storing on self

        Archives.posts should be sorted by date, newest first.
        """
        arch = Archives(posts=self.posts, settings=self.settings)
        sorted_posts = sorted(self.posts, reverse=True)
        self.assertEqual(arch.posts, sorted_posts)

    def test_Archives_sets_key_variables(self):
        """Archives should set key variables required by BlogObject"""
        arch = Archives(posts=self.posts, settings=self.settings)
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
        self.settings = load_settings(files=[settings_path],
                                      local=False)
        starting_date = datetime(2015, 9, 22, 19)
        self.posts = [
            Post(title='post {}'.format(i), body='Here’s some text!',
                 date=starting_date - timedelta(i),
                 settings=self.settings)
            for i in range(40)
            ]
        random.shuffle(self.posts)      # Ensure not sorted

    def test_PostsCollection_store_posts(self):
        """PostsCollection stores a list of posts newest-first"""
        coll = PostsCollection(posts=self.posts,
                               settings=self.settings)
        self.assertEqual(sorted(self.posts, reverse=True), coll.posts)

    def test_PostsCollection_iterator(self):
        """PostsCollection can be iterated over"""
        coll = PostsCollection(posts=self.posts,
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
        os.chdir(TEST_BLOG_DIR)
        settings_path = TEST_BLOG_DIR.joinpath('settings.json')
        self.settings = load_settings(files=[settings_path],
                                      local=False)
        self.output_dir = Path(self.settings['paths']['output root'])
        self.files = [
            Post(title='', slug='post', date=datetime(2015, 1, 1),
                 body='', settings=self.settings),
            Page(title='', slug='page', body='',
                 settings=self.settings),
            Index(posts=[], settings=self.settings, page_number=1),
        ]
        # Make dummy files and directories
        for f in self.files:
            f.output_path.parent.mkdir(parents=True, exist_ok=True)
            f.output_path.touch()

    def tearDown(self):
        """Clean up dummy files"""
        shutil.rmtree(str(self.output_dir))

    def test_Sitemap_sets_key_variables(self):
        """Sitemap should set key variables required by BlogObject"""
        sitemap = Sitemap(content=[], settings=self.settings)
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

        sitemap = Sitemap(content=self.files, settings=self.settings)
        self.assertEqual(expected, sitemap.url_date_pairs)

    def test_Sitemap_iter(self):
        """Iterating over Sitemap produces tuples of (str, datetime)"""
        sitemap = Sitemap(content=self.files, settings=self.settings)
        expected_types = [str, datetime]
        for item in sitemap:
            self.assertEqual(expected_types, [type(x) for x in item])


class TestRSSFeed(unittest.TestCase):
    """Test the RSSFeed class"""
    def setUp(self):
        settings_path = TEST_BLOG_DIR.joinpath('settings.json')
        self.settings = load_settings(files=[settings_path],
                                      local=False)
        self.number_of_posts = 5
        self.settings['feeds']['number of posts'] = self.number_of_posts

        starting_date = datetime(2015, 9, 22, 19)
        self.posts = [
            Post(title='post {}'.format(i), body='Here’s some text!',
                 date=starting_date - timedelta(i),
                 settings=self.settings)
            for i in range(40)
            ]
        random.shuffle(self.posts)      # Ensure not sorted

    def test_RSSFeed_init_limit_posts(self):
        """RSSFeed sets self.posts to subset of posts arg on init

        The number of posts in RSSFeed.posts should equal self.number_of_posts.
        """
        feed = RSSFeed(posts=self.posts, settings=self.settings)
        self.assertEqual(len(feed.posts), self.number_of_posts)

    def test_RSSFeed_init_posts_sorted(self):
        """RSSFeed sets self.posts to sorted subset of posts arg on init

        RSSFeed.posts should be sorted by date, newest first.
        """
        feed = RSSFeed(posts=self.posts, settings=self.settings)
        sorted_posts = sorted(self.posts, reverse=True)[:self.number_of_posts]
        self.assertEqual(feed.posts, sorted_posts)

    def test_RSSFeed_sets_key_variables(self):
        """RSSFeed should set key variables required by BlogObject"""
        feed = RSSFeed(posts=self.posts, settings=self.settings)
        self.assertEqual(feed._path_template_key, 'rss path template')
        self.assertEqual(feed._template_file_key, 'rss')


class TestJSONFeed(unittest.TestCase):
    """Test the JSONFeed class"""
    def setUp(self):
        os.chdir(TEST_BLOG_DIR)
        settings_path = TEST_BLOG_DIR.joinpath('settings.json')
        self.settings = load_settings(files=[settings_path],
                                      local=False)
        self.output_dir = Path(self.settings['paths']['output root'])
        self.number_of_posts = 5
        self.settings['feeds']['number of posts'] = self.number_of_posts

        starting_date = datetime(2015, 9, 22, 19)
        self.posts = [
            Post(title='post {}'.format(i),
                 body='Here’s some text! And [a relative URL](/about)',
                 date=starting_date - timedelta(i),
                 settings=self.settings)
            for i in range(40)
            ]
        random.shuffle(self.posts)      # Ensure not sorted

    def tearDown(self):
        """Clean up dummy files"""
        if self.output_dir.exists():
            shutil.rmtree(str(self.output_dir))

    def test_JSONFeed_init_limit_posts(self):
        """JSONFeed sets self.posts to subset of posts arg on init

        The number of posts in JSONFeed.posts should equal self.number_of_posts
        """
        feed = JSONFeed(posts=self.posts, settings=self.settings)
        self.assertEqual(len(feed.posts), self.number_of_posts)

    def test_JSONFeed_init_posts_sorted(self):
        """JSONFeed sets self.posts to sorted subset of posts arg on init

        JSONFeed.posts should be sorted by date, newest first.
        """
        feed = JSONFeed(posts=self.posts, settings=self.settings)
        sorted_posts = sorted(self.posts, reverse=True)[:self.number_of_posts]
        self.assertEqual(feed.posts, sorted_posts)

    def test_JSONFeed_sets_key_variables(self):
        """JSONFeed should set path template but not template file"""
        feed = JSONFeed(posts=self.posts, settings=self.settings)
        self.assertEqual(feed._path_template_key, 'json feed path template')
        with self.assertRaises(NotImplementedError):
            feed._template_file_key

    def test_JSONFeed_is_valid(self):
        """JSONFeed should write a valid JSON Feed file to disk

        JSONFeed must override the default BlogObject write_to_disk
        because it doesn't use the Jinja templating that the rest of
        the site's content (HTML or XML) needs.
        """
        test_posts = [self.posts[0], self.posts[1]]
        feed = JSONFeed(posts=test_posts, settings=self.settings)
        feed.render_to_disk()
        json_file = Path(self.settings['paths']['output root'],
                         self.settings['paths']['json feed path template'])
        output = json.loads(json_file.read_text(encoding='utf-8'))
        root_data = (
            ('version', 'https://jsonfeed.org/version/1'),
            ('title', self.settings['site']['title']),
            ('home_page_url', self.settings['site']['url']),
            ('feed_url',
             urljoin(self.settings['site']['url'],
                     self.settings['paths']['json feed path template'])),
            ('description', self.settings['site']['description']),
            ('author', {'name': 'Example Name',
                        'url': 'http://www.example.com/about',
                        'avatar': 'https://www.placehold.it/512'}),
            ('icon', 'https://www.placehold.it/512'),
            ('favicon', 'https://www.placehold.it/64')
            )
        for key, value in root_data:
            with self.subTest(msg=f'{key} -- {value}'):
                self.assertEqual(output[key], value)

        expected_items = [
            {'id': post.url,
             'url': post.url,
             'title': post.title,
             'content_html':
                absolute_urls(post.html, self.settings['site']['url']),
             'date_published': post.date.isoformat(timespec='seconds')
             }
            for post in test_posts
            ]

        expected_items.sort(key=lambda p: p['id'])
        output['items'].sort(key=lambda p: p['id'])
        self.assertEqual(expected_items, output['items'])
