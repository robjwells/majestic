from datetime import datetime
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
        extensions = ['.md', '.mkd', '.mdown', '.mkdown', '.markdown']
        test_files = [f for f in posts_dir.iterdir() if f.suffix in extensions]
        self.assertEqual(test_files, list(files))

    def test_markdown_files_empty_dir(self):
        """result is empty when given empty dir"""
        temp_dir = pathlib.Path(tempfile.mkdtemp())
        files = majestic.markdown_files(temp_dir)
        self.assertFalse(list(files))
        temp_dir.rmdir()

    def test_markdown_files_nonempty_dir_no_md(self):
        """result is empty when given nonempty dir containing no md files"""
        temp_dir = pathlib.Path(tempfile.mkdtemp())
        for x in range(20):
            temp_dir.touch(x)
        files = majestic.markdown_files(temp_dir)
        self.assertFalse(list(files))
        for file in temp_dir.iterdir():
            file.unlink()
        temp_dir.rmdir()


class TestContent(unittest.TestCase):
    """Test the main Page and Post classes"""
    def setUp(self):
        """Set dummy values for use in testing"""
        self.title = "Here’s a — test! — dummy title: (with lots o' symbols)"
        self.date = datetime(2015, 8, 22, 9, 46)
        self.slug = 'test-slug-with-no-relation-to-title'
        self.meta = {'tags': ['a', 'b']}
        self.body = (
            # http://slipsum.com
            "You see? It's curious. Ted did figure it out - time"
            "travel. And when we get back, we gonna tell everyone. How"
            "it's possible, how it's done, what the dangers are. But"
            "then why fifty years in the future when the spacecraft"
            "encounters a black hole does the computer call it an"
            "'unknown entry event'? Why don't they know? If they don't"
            "know, that means we never told anyone. And if we never"
            "told anyone it means we never made it back. Hence we die"
            "down here. Just as a matter of deductive logic."
            "\n\n"
            "You see? It's curious. Ted did figure it out - time"
            "travel. And when we get back, we gonna tell everyone. How"
            "it's possible, how it's done, what the dangers are. But"
            "then why fifty years in the future when the spacecraft"
            "encounters a black hole does the computer call it an"
            "'unknown entry event'? Why don't they know? If they don't"
            "know, that means we never told anyone. And if we never"
            "told anyone it means we never made it back. Hence we die"
            "down here. Just as a matter of deductive logic."
            "\n\n"
            "The lysine contingency - it's intended to prevent the"
            "spread of the animals is case they ever got off the"
            "island. Dr. Wu inserted a gene that makes a single faulty"
            "enzyme in protein metabolism. The animals can't"
            "manufacture the amino acid lysine. Unless they're"
            "continually supplied with lysine by us, they'll slip into"
            "a coma and die."
            )

    def test_page_init(self):
        """init with valid values returns a Page with same values"""
        page = majestic.Page(title=self.title, body=self.body,
                             slug=self.slug, **self.meta)
        self.assertEqual(
            [self.title, self.body, self.slug, self.meta],
            [page.title, page.body, page.slug, page.meta]
            )

    def test_post_init(self):
        """init with valid values returns a Post with same values"""
        post = majestic.Post(title=self.title, date=self.date,
                             slug=self.slug, body=self.body,
                             **self.meta)
        self.assertIsInstance(post, majestic.Post)
        self.assertEqual(
            [self.title, self.date, self.slug, self.body, self.meta],
            [post.title, post.date, post.slug, post.body, post.meta]
            )

    def test_post_init_invalid_date(self):
        """Post raises if date is not a datetime object"""
        with self.assertRaises(ValueError):
            majestic.Post(
                date='a string',
                title=self.title,
                slug=self.slug,
                body=self.body
                )


class TestParseFile(unittest.TestCase):
    """Test that parse_file correctly processes markdown pages and posts"""
    def setUp(self):
        self.pages = TEST_BLOG_DIR.joinpath('pages').iterdir()
        self.posts = TEST_BLOG_DIR.joinpath('posts').iterdir()

    def test_parsed_type(self):
        """Object returned is of correct content type

        Test both Pages and Posts
        """
        parsed_pages = [majestic.parse_file(page, content=majestic.Page)
                        for page in self.pages]
        # Check the function returned the right number of objects
        # (This is mostly in here so that the test doesn't pass when
        #  the function just contains the `pass` statement)
        self.assertEqual(len(parsed_pages), len(list(self.pages)))
        for page in parsed_pages:
            self.assertTrue(type(page) == majestic.Page)

        parsed_posts = [majestic.parse_file(post, content=majestic.Post)
                        for post in self.posts]
        self.assertEqual(len(parsed_posts), len(list(self.posts)))
        for post in parsed_pages:
            self.assertTrue(type(post) == majestic.Post)


if __name__ == '__main__':
    unittest.main(verbosity=2)
