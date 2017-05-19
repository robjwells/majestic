import unittest
import majestic.utils as utils

import string


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
        new_slug = utils.normalise_slug(known_bad_slug)
        self.assertEqual(new_slug, expected)

    def test_normalise_slug_chars(self):
        """normalise_slug function returns a valid slug

        A valid slug is deemed to contain only the following characters:

        a-z 0-9 - . _ ~
        """
        bad_set = set(" :/?#[]@!$&'()*+,;=")
        good_set = set(string.ascii_lowercase + string.digits + '-')

        test_bad_slug = "this is an :/?#[]@!$&'()*+,;= invalid slug"
        new_slug = utils.normalise_slug(test_bad_slug)
        self.assertTrue(set(new_slug).issubset(good_set))
        self.assertTrue(set(new_slug).isdisjoint(bad_set))

        test_good_slug = "00-this-is-a-valid-slug"
        self.assertEqual(utils.normalise_slug(test_good_slug),
                         test_good_slug)

    def test_normalise_slug_empty_string(self):
        """normalise_slug should raise if result is the empty string"""
        with self.assertRaises(ValueError):
            utils.normalise_slug(":/?#[]@!$&'()*+,;=")

    def test_normalise_slug_conservative(self):
        """Normalise correctly removes unreserved chars . _ ~

        Those characters pass the validator but should still be removed
        if the slug is normalised because of another character.
        """
        slug = 'here are some valid chars . _ ~ and an invalid one!'
        normalised = utils.normalise_slug(slug)
        self.assertEqual(
            normalised,
            'here-are-some-valid-chars-and-an-invalid-one'
            )

    def test_normalise_slug_percent_encoding(self):
        """normalise_slug removes percent-encoded characters"""
        slug = 'this%20slug%20has%20spaces'
        normalised = utils.normalise_slug(slug)
        self.assertEqual(normalised, 'this-slug-has-spaces')

    def test_validate_slug_empty(self):
        """validate_slug returns False if slug is the empty string"""
        self.assertFalse(utils.validate_slug(''))

    def test_validate_slug_false(self):
        """validate_slug returns False if slug contains invalid characters"""
        known_bad_slug = "This is a completely invalid slug :/?#[]@!$&'()*+,;="
        self.assertFalse(utils.validate_slug(known_bad_slug))

    def test_validate_slug_bad_percent(self):
        """validate_slug returns False if slug has bad percent encoding"""
        known_bad_slug = "this-is-not-100%-valid"
        self.assertFalse(utils.validate_slug(known_bad_slug))

    def test_validate_slug_good_percent(self):
        """validate_slug returns True given proper percent encoding"""
        known_good_slug = 'hello%20world'
        self.assertTrue(utils.validate_slug(known_good_slug))

    def test_validate_slug_true(self):
        """validate_slug returns True when slug contains all valid chars"""
        known_good_slug = "00-this-is_a~valid.slug"
        self.assertTrue(utils.validate_slug(known_good_slug))

    def test_validate_slug_nonascii(self):
        """validate_slug returns False when slug contains non-ASCII chars

        This is an important test because non-ASCII chars fall between
        the characters in the reserved set and the unreserved set.
        """
        slug = 'lets-go-to-the-café'
        self.assertFalse(utils.validate_slug(slug))


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
        result = utils.chunk(self.data, 5)
        self.assertEqual(expected, list(result))

    def test_chunk_3(self):
        """Take chunks of 3 elements from self.data"""
        expected = ['ABC', 'DEF', 'GHI', 'J']
        result = utils.chunk(self.data, 3)
        self.assertEqual(expected, list(result))


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
<link href="/resources/my-stylesheet.css"/>
</head>
<p><a href="/latin">Lorem ipsum</a>.</p>
        '''.strip()
        expected = '''\
<head>
<link href="http://example.com/resources/my-stylesheet.css"/>
</head>
<p><a href="http://example.com/latin">Lorem ipsum</a>.</p>
        '''.strip()
        result = utils.absolute_urls(html=html, base_url=self.base_url)
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
        result = utils.absolute_urls(html=html, base_url=self.base_url)
        self.assertEqual(expected, result)
