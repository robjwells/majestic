import os
import pathlib
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
        default_cfg = str(MAJESTIC_DIR.joinpath('majestic.cfg'))
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
    def test_markdown_files(self):
        """markdown_files generates expected list for test-blog/posts"""
        posts_dir = TEST_BLOG_DIR.joinpath('posts')
        files = majestic.markdown_files(posts_dir)
        extensions = ['.md', '.mkd', '.mkdown', '.markdown']
        test_files = [f for f in posts_dir.iterdir() if f.suffix in extensions]
        self.assertEqual(test_files, list(files))

    def test_markdown_files_empty_dir(self):
        """result is empty when given empty dir"""
        temp_dir = pathlib.Path(tempfile.mkdtemp())
        files = majestic.markdown_files(temp_dir)
        self.assertFalse(list(files))
        temp_dir.rmdir()


if __name__ == '__main__':
    unittest.main(verbosity=2)
