#!/usr/bin/env python

import configparser
import datetime
import os
import pathlib
import re
import string
from unidecode import unidecode

MAJESTIC_DIR = pathlib.Path(__file__).resolve().parent


def load_settings(default=True, local=True, files=None):
    """Load config from standard locations and specified files

    default:    load default config file
    local:      load config file from current directory
    files:      [str] of filenames to load
    """
    settings = configparser.ConfigParser(interpolation=None)
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


def markdown_files(directory):
    """Return a generator of the markdown files found by walking directory

    directory:  a pathlib.Path

    Accepted extenions for markdown files:
        * md
        * mkd
        * mdown
        * mkdown
        * markdown
    """
    extensions = {'.md', '.mkd', '.mdown', '.mkdown', '.markdown'}
    files = (pathlib.Path(os.path.join(dirpath, f))
             for dirpath, dirnames, filenames in os.walk(str(directory))
             for f in filenames
             if os.path.splitext(f)[1] in extensions)
    return files


class Content(object):
    """Content object representing a markdown post or page"""
    def __init__(self, title, body, slug, date=None,
                 source_path=None, **kwargs):
        """Initialise Post

        title:          str
        body:           str
        slug:           str
        date:           datetime (if not None)
        source_path:    pathlib.Path (if not None)

        source_path can be None to allow programmatic Content creation
        kwargs used to create metadata container self.meta
        """
        self.title = title
        self.body = body
        self.slug = slug
        self.meta = kwargs
        if date is not None and not isinstance(date, datetime.datetime):
            raise ValueError('date must be a datetime.datetime object')
        self.date = date
        if (source_path is not None and
            not isinstance(source_path, pathlib.Path)):
            raise ValueError('source_path must be a pathlib.Path object')
        self.source_path = source_path

    def __lt__(self, other):
        """Compare self with other based on date, title then slug

        If both self and other have dates, compare dates.
        If not, or if the dates are the same, compare titles.
        If titles are the same then compare slugs.

        Titles and slugs are compared case-insensitively.
        """
        if all([self.date, other.date]):
            return self.date < other.date
        elif self.title.lower() != other.title.lower():
            return self.title.lower() < other.title.lower()
        else:
            return self.slug.lower() < other.slug.lower()


def validate_slug(slug):
    """Test slug for validity and return a boolean

    Slugs containing the following characters are deemed to be
    invalid (note the quoted space at the beginning):

    " " : / ? # [ ] @ ! $ & ' ( ) * + , ; =

    (This is the reserved set according to IETF RFC 3986, with the
    addition of the space character.)

    Slugs containing a percent character that is not followed by
    two hex digits are also deemed to be invalid.
    """
    bad_chars = set(" :/?#[]@!$&'()*+,;=")
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


def parse_file(file, settings):
    """Create a content object from the contents of file

    file:       a pathlib.Path
    settings:   a ConfigParser object containing the site's settings
    """
    date_format = settings.get('dates', 'date format')

    with file.open() as f:
        meta, body = f.read().split('\n\n', maxsplit=1)
    body = body.strip('\n')
    meta = [line.split(':', maxsplit=1) for line in meta.splitlines()]
    meta = {k.lower().strip(): v.strip() for k, v in meta}
    if 'date' in meta:
        meta['date'] = datetime.datetime.strptime(meta['date'], date_format)
    if not validate_slug(meta['slug']):
        meta['slug'] = normalise_slug(meta['slug'])
    meta['source_path'] = file
    return Content(body=body, **meta)
