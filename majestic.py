#!/usr/bin/env python

import configparser
import datetime
import pathlib
import re
import string
from unidecode import unidecode

MAJESTIC_DIR = pathlib.Path(__file__).resolve().parent


def load_settings(default=True, local=True, files=None):
    """Load specified config files or the default and local ones

    default:    load default config file
    local:      load config file from current directory
    files:      [str] of filenames to load
    """
    settings = configparser.ConfigParser()
    if files is None:
        files = []
    if local:
        local_cfg = pathlib.Path.cwd().joinpath('settings.cfg')
        files.insert(0, str(local_cfg))
    if default:
        default_cfg = MAJESTIC_DIR.joinpath('majestic.cfg')
        files.insert(0, str(default_cfg))
    settings.read(files)
    return settings


def markdown_files(dir):
    """Return a generator of all of the markdown files found in dir

    dir:    a pathlib.Path

    Acceptable extenions for markdown files:
        * md
        * mkd
        * mdown
        * mkdown
        * markdown
    """
    extensions = {'.md', '.mkd', '.mdown', '.mkdown', '.markdown'}
    return (file for file in dir.iterdir() if file.suffix in extensions)


class Page(object):
    """Basic content object

    Has a title, body, slug (for the URL) and optional metadata"""
    def __init__(self, title, body, slug, **kwargs):
        """Initialise Page

        title:  str
        body:   str
        slug:   str

        metadata container self.meta built from unused kwargs
        """
        self.title = title
        self.body = body
        self.slug = slug
        self.meta = kwargs


class Post(Page):
    """Content object representing a blog post

    Has all the attributes of Page (title, body, slug, meta via kwargs)
    but with the addition of a date
    """
    def __init__(self, title, body, slug, date, **kwargs):
        """Initialise Post

        title:  str
        body:   str
        slug:   str
        date:   datetime
        """
        super().__init__(title=title, body=body, slug=slug, **kwargs)
        if not isinstance(date, datetime.datetime):
            raise ValueError('date must be a datetime.datetime object')
        self.date = date


def is_valid_slug(slug):
    """Test slug for validity and return a boolean

    Slugs containing the following characters are deemed to be
    invalid (note the quoted space at the beginning):

    " " : ? # [ ] @ ! $ & ' ( ) * + , ; =

    Slugs containing a percent character that is not followed by
    two hex digits are also deemed to be invalid.
    """
    bad_chars = set(" :?#[]@!$&'()*+,;=")
    hex_set = set(string.hexdigits)

    is_empty_string = len(slug) == 0
    contains_bad_chars = bool(set(slug) & bad_chars)

    contains_bad_percent = False
    for match in re.finditer(r'%(.{,2})', slug):
        encoded = match.group(1)
        if len(encoded) < 2 or not set(encoded).issubset(hex_set):
            contains_bad_percent = True
    return not (is_empty_string or contains_bad_chars or contains_bad_percent)


def normalise_slug(slug):
    """Rewrite slug to contain only valid characters

    Valid characters are deemed to be:

    a-z 0-9 - . _ ~

    Any other characters (including percent encoded characters)
    are removed from the output.

    Spaces are changed to hyphens.

    This function borrows heavily from Dr Drang's post ASCIIfying:
    http://www.leancrew.com/all-this/2014/10/asciifying/
    """
    separators = re.compile(r'[—–/:;,]')
    not_valid = re.compile(r'[^- ._~a-z0-9]')  # Spaces handled separately
    hyphens = re.compile(r'-+')

    new_slug = slug.lower()
    new_slug = separators.sub('-', new_slug)
    new_slug = unidecode(new_slug)
    new_slug = not_valid.sub('', new_slug)
    new_slug = new_slug.replace(' ', '-')
    new_slug = hyphens.sub('-', new_slug)
    new_slug = new_slug.strip('-')

    if not new_slug:
        raise ValueError('Slug is the empty string')

    return new_slug


def parse_file(file, content):
    """Create a content object from the contents of file

    file:       a pathlib.Path
    content:    Page or one of its subclasses
    """
    # This will have to change when the config file is implemented
    date_format = '%Y-%m-%d %H:%M'

    with file.open() as f:
        meta, body = f.read().split('\n\n', maxsplit=1)
    body = body.strip('\n')
    meta = [line.split(':', maxsplit=1) for line in meta.splitlines()]
    meta = {k.lower().strip(): v.strip() for k, v in meta}
    if 'date' in meta:
        meta['date'] = datetime.datetime.strptime(meta['date'], date_format)
    if not is_valid_slug(meta['slug']):
        meta['slug'] = normalise_slug(meta['slug'])
    return content(body=body, **meta)
