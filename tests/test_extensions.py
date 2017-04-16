import unittest
from majestic import load_settings
from majestic.content import Post, Page
from majestic.utils import load_extensions
from majestic.extensions import ExtensionStage, apply_extensions

from datetime import datetime
import tempfile
import os
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent
MAJESTIC_DIR = TESTS_DIR.parent.joinpath('majestic')
TEST_BLOG_DIR = TESTS_DIR.joinpath('test-blog')


class TestExtensions(unittest.TestCase):
    """Test the mechanisms for loading and applying extensions"""
    def setUp(self):
        os.chdir(str(TEST_BLOG_DIR))
        self.settings = load_settings()
        ext_dir_name = self.settings['paths']['extensions root']
        self.ext_dir = TEST_BLOG_DIR.joinpath(ext_dir_name)
        self.posts = [Post(title='test', body='test',
                           date=datetime.now(),
                           settings=self.settings)]
        self.pages = [Page(title='test', body='test',
                           settings=self.settings)]

    def test_load_extensions(self):
        """load_extensions returns expected extensions from directory"""
        expected_names = [fn.stem for fn in self.ext_dir.iterdir()
                          if fn.suffix == '.py']
        result = load_extensions(self.ext_dir)
        result_names = [m.__name__ for m in result]
        self.assertEqual(expected_names, result_names)

    def test_load_extensions_empty(self):
        """load_extensions returns empty list for directory with no modules"""
        with tempfile.TemporaryDirectory() as ext_dir:
            ext_dir_path = Path(ext_dir)
            result = load_extensions(ext_dir_path)
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
        extensions = load_extensions(self.ext_dir)

        result = apply_extensions(
            stage=ExtensionStage.posts_and_pages,
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
        extensions = load_extensions(self.ext_dir)
        objs = self.posts + self.pages
        result = apply_extensions(
            stage=ExtensionStage.objects_to_write,
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
        result = apply_extensions(
            stage=ExtensionStage.posts_and_pages,
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
        result = apply_extensions(
            stage=ExtensionStage.objects_to_write,
            modules=[], objects=[], settings=self.settings)
        self.assertEqual(keys, set(result))
