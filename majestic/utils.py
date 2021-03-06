import json
import os
from pathlib import Path
import re
import string
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from unidecode import unidecode


MAJESTIC_DIR = Path(__file__).resolve().parent


def validate_slug(slug):
    """Test slug for validity and return a boolean

    Slugs containing any characters other than those in the unreserved
    set according to IETF RFC 3986 are deemed to be invalid. Other
    than percent-encoded characters, the acceptable characters are:

    a-z A-Z 0-9 - . _ ~

    Note that only ASCII alphabetic characters are allowed. (Covered by
    the inclusive ranges 0x41-0x5A and 0x61-0x7A.)

    Slugs containing a percent character that is not followed by
    two hex digits are also deemed to be invalid.

    The use of capital letters, periods, underscores and tildes in slugs
    is acceptable but discouraged.
    """
    good_chars = set(string.ascii_letters + string.digits + '-._~' + '%')
    hex_set = set(string.hexdigits)

    is_empty_string = len(slug) == 0
    contains_bad_chars = bool(set(slug) - good_chars)

    contains_bad_percent = False
    for match in re.finditer(r'%(.{,2})', slug):
        encoded = match.group(1)
        if len(encoded) < 2 or not set(encoded).issubset(hex_set):
            contains_bad_percent = True
    return not (is_empty_string or contains_bad_chars or contains_bad_percent)


def normalise_slug(slug):
    """Rewrite slug to contain only valid characters

    Valid characters are deemed to be:

    a-z 0-9 -

    Any other characters (including percent encoded characters)
    are removed from the output. Note that this function is more
    strict with the characters it emits than validate_slug is
    with the characters that it accepts.

    Spaces are changed to hyphens.

    This function borrows heavily from Dr Drang's post ASCIIfying:
    http://www.leancrew.com/all-this/2014/10/asciifying/
    """
    separators = re.compile(r'[—–/:;,.~_]')
    percent_enc = re.compile(r'%[0-9a-f]{2}')
    not_valid = re.compile(r'[^- a-z0-9]')  # Spaces handled separately
    hyphens = re.compile(r'-+')

    new_slug = slug.lower()
    new_slug = separators.sub('-', new_slug)
    new_slug = percent_enc.sub('-', new_slug)
    new_slug = unidecode(new_slug)
    new_slug = not_valid.sub('', new_slug)
    new_slug = new_slug.replace(' ', '-')
    new_slug = hyphens.sub('-', new_slug)
    new_slug = new_slug.strip('-')

    if not new_slug:
        raise ValueError('Slug is the empty string')

    return new_slug


def chunk(iterable, chunk_length):
    """Yield the members of its iterable chunk_length at a time

    If the length of the iterable is not a multiple of the chunk length,
    the final chunk contains the remaining data but does not fill to
    meet the chunk length (unlike the grouper recipe in the
    itertools documentation).
    """
    for idx in range(0, len(iterable), chunk_length):
        yield iterable[idx:idx + chunk_length]


def markdown_files(directory):
    """Return a generator of the markdown files found by walking directory

    Accepted extenions for markdown files:
        * md
        * mkd
        * mdown
        * mkdown
        * markdown
    """
    extensions = {'.md', '.mkd', '.mdown', '.mkdown', '.markdown'}
    files = (Path(dirpath, f)
             for dirpath, dirnames, filenames in os.walk(str(directory))
             for f in filenames if Path(f).suffix in extensions)
    return files


def load_settings(default=True, local=True, files=None):
    """Load config from standard locations and specified files

    default:    bool, load default config file
    local:      bool, load config file from current directory
    files:      list of filenames to load
    """
    if files is None:
        files = []
    if local:
        files.insert(0, Path.cwd().joinpath('settings.json'))
    if default:
        files.insert(0, MAJESTIC_DIR.joinpath('majestic.json'))
    settings = {}
    for file in files:
        with open(file) as json_file:
            from_file = json.load(json_file)
            # Merge settings
            for key in from_file:
                if key in settings:
                    if isinstance(settings[key], dict):
                        settings[key].update(from_file[key])
                    elif isinstance(settings[key], list):
                        settings[key].extend(from_file[key])
                else:
                    settings[key] = from_file[key]
    return settings


def absolute_urls(html, base_url):
    """Change relative URLs in html to absolute URLs using base_url

    Arguments:
        html:           str containing HTML markup
        base_url:       str containing a URL
    """
    parsed_html = BeautifulSoup(html, 'html.parser')
    for attr in ['href', 'src', 'poster']:
        for tag in parsed_html.select('[{0}]'.format(attr)):
            tag_url = tag[attr]
            if not urlparse(tag_url).netloc:
                tag[attr] = urljoin(base_url, tag_url)
    return str(parsed_html)
