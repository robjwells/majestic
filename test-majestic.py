import unittest

import majestic


class TestLoadSettings(unittest.TestCase):
    """Default and site-specific settings tests"""

    def test_load_default_settings(self):
        """Config class contains setting set only in default .cfg file"""
        settings = majestic.load_settings()
        self.assertTrue(settings.getboolean('testing', 'default cfg loaded'))



if __name__ == '__main__':
    unittest.main(verbosity=2)
