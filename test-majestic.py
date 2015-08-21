import pathlib
import unittest

import majestic

MAJESTIC_DIR = pathlib.Path(__file__).resolve().parent
TEST_BLOG_DIR = MAJESTIC_DIR.joinpath('test-blog')

class TestLoadSettings(unittest.TestCase):
    """Default and site-specific settings tests"""

    def test_load_default_settings(self):
        """Config class contains setting set only in default .cfg file"""
        settings = majestic.load_settings()
        self.assertTrue(settings.getboolean('testing', 'default cfg loaded'))

    def test_load_specific_only(self):
        """When given filenames, load only those files"""
        test_settings_fn = str(TEST_BLOG_DIR.joinpath('settings.cfg'))
        settings = majestic.load_settings([test_settings_fn])
        self.assertTrue(settings.getboolean('testing', 'test-blog cfg loaded'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
