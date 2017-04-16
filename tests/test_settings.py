import unittest
from majestic.utils import load_settings

import os
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
TEST_BLOG_DIR = TESTS_DIR.joinpath('test-blog')


class TestLoadSettings(unittest.TestCase):
    """Default and site-specific settings tests"""
    def setUp(self):
        os.chdir(str(TESTS_DIR))

    def test_load_default_settings(self):
        """Config class contains setting set only in default config file"""
        settings = load_settings(default=True, local=False)
        self.assertTrue(settings['testing']['default cfg loaded'])

    def test_load_specific_only_str(self):
        """When given filenames (as str), load only those files"""
        test_settings_fn = str(TEST_BLOG_DIR.joinpath('settings.json'))
        settings = load_settings(default=False, local=False,
                                 files=[test_settings_fn])
        self.assertTrue(settings['testing']['test-blog cfg loaded'])

    def test_load_specific_only_Path(self):
        """When given filenames (as pathlib.Path), load only those files

        Tests that load_settings correctly handles paths given as
        pathlib.Path instead of str (as os functions expect).
        The burden of conversion should fall on the function
        itself, not its callers.
        """
        test_settings_fn = TEST_BLOG_DIR.joinpath('settings.json')
        settings = load_settings(default=False, local=False,
                                 files=[test_settings_fn])
        self.assertTrue(settings['testing']['test-blog cfg loaded'])

    def test_load_default_and_local(self):
        """Properly load defaults and settings.json in current directory"""
        os.chdir(str(TEST_BLOG_DIR))
        settings = load_settings(default=True, local=True)
        self.assertTrue(settings['testing']['test-blog cfg loaded'])
        self.assertTrue(settings['testing']['default cfg loaded'])

    def test_defaults_overriden_by_local(self):
        """Config files loaded in order so that locals override defaults"""
        default_settings = load_settings(default=True, local=False)
        overridden_value = default_settings['testing']['overridden setting']
        self.assertFalse(overridden_value)
        os.chdir(str(TEST_BLOG_DIR))
        combined_settings = load_settings()
        overridden_value = combined_settings['testing']['overridden setting']
        self.assertTrue(overridden_value)

    def test_settings_empty_when_not_given_anything(self):
        """Returned config object should be empty when everything disabled"""
        settings = load_settings(default=False, local=False)
        self.assertFalse(settings)
