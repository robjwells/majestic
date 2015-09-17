#!/usr/bin/env python

import configparser
import datetime
import markdown
import os
import pathlib
import pytz
import re
import string
from unidecode import unidecode
import urllib.parse

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
    """Base class for content"""
    def __init__(self, *, title, body, settings,
                 slug=None, source_path=None, **kwargs):
        """Initialise Content

        title:          str
        body:           str
        slug:           str (if not None)
        source_path:    pathlib.Path (if not None)

        If slug is None, a slug is created from title.

        source_path can be None to allow programmatic Content creation
        kwargs used to create metadata container self.meta.
        """
        self.title = title
        self.body = body
        self.settings = settings
        if slug is None:
            slug = normalise_slug(title)
        elif not validate_slug(slug):
            slug = normalise_slug(slug)
        self.slug = slug
        self.source_path = source_path
        self.meta = kwargs

        # Placeholders
        self._html = None
        self._output_path = None
        self._url = None

    def __lt__(self, other):
        """Compare self with other based on title and slug

        Slugs are compared if titles are the same.
        Both checks are case-insensitive.
        """
        if self.title.lower() != other.title.lower():
            return self.title.lower() < other.title.lower()
        else:
            return self.slug.lower() < other.slug.lower()

    @property
    def html(self):
        """Render self.body markdown text as HTML

        Uses the extensions stored in the config file under [markdown] as
        a whitespace-separated list under the 'extensions' property

        'markdown.extensions.' is added to members of the extension list
        that are missing it
        """
        if self._html is None:
            extensions = self.settings['markdown']['extensions'].split()
            prefix = 'markdown.extensions.'
            for idx, ext in enumerate(extensions):
                if not ext.startswith(prefix):
                    extensions[idx] = prefix + ext
            md = markdown.Markdown(extensions=extensions)
            self._html = md.convert(self.body)
        return self._html

    @property
    def output_path(self):
        """On subclasses, return the content's output path

        This raises NotImplementedError on the Content base class"""
        raise NotImplementedError()

    @property
    def url(self):
        """On subclasses, return the content's URL

        This raises NotImplementedError on the Content base class
        """
        raise NotImplementedError()


class Page(Content):
    """A Content subclass representing a static Page

    Page is largely just a concrete version of Content, with the stub
    methods implemented.
    """
    @property
    def output_path(self):
        """Path to Page's output file"""
        if self._output_path is None:
            output_dir = self.settings['paths']['output root']
            path = self.settings['paths']['page output'].format(content=self)
            self._output_path = pathlib.Path(output_dir).joinpath(path)
        return self._output_path

    @property
    def url(self):
        """Page's URL"""
        if self._url is None:
            site_url = self.settings['site']['url']
            path = self.settings['paths']['page output'].format(content=self)
            self._url = urllib.parse.urljoin(site_url, path)
        return self._url


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
    """Create a Content object from the contents of file

    Returns None if the file is a draft, by these criteria:
        * date is in the future.
        * draft appears alone on a line in the header.
          Note that this is sensitive to extra whitespace.

    file:       a pathlib.Path
    settings:   a ConfigParser object containing the site's settings
    """
    with file.open() as f:
        meta, body = f.read().split('\n\n', maxsplit=1)
    body = body.strip('\n')
    meta = [line.split(':', maxsplit=1) for line in meta.splitlines()]
    if ['draft'] in meta:
        return None
    meta = {k.lower().strip(): v.strip() for k, v in meta}

    if 'date' in meta:
        timezone = pytz.timezone(settings['dates']['timezone'])
        date_format = settings['dates']['date format']
        post_date = datetime.datetime.strptime(meta['date'], date_format)
        post_date = timezone.localize(post_date)
        if post_date > timezone.localize(datetime.datetime.now()):
            return None
        meta['date'] = post_date

    if not validate_slug(meta['slug']):
        meta['slug'] = normalise_slug(meta['slug'])

    meta['source_path'] = file

    return Content(body=body, **meta)
