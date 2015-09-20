#!/usr/bin/env python

from configparser import ConfigParser
from datetime import datetime
import json
import math
import os
from pathlib import Path
import re
import string
from urllib.parse import urljoin

import jinja2
import markdown
import pytz
from unidecode import unidecode

MAJESTIC_DIR = Path(__file__).resolve().parent
MAJESTIC_JINJA_OPTIONS = {
    'auto_reload': False,
    }


def load_settings(default=True, local=True, files=None):
    """Load config from standard locations and specified files

    default:    load default config file
    local:      load config file from current directory
    files:      [str] of filenames to load
    """
    settings = ConfigParser(interpolation=None)
    if files is None:
        files = []
    if local:
        local_cfg = Path.cwd().joinpath('settings.cfg')
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
    files = (Path(dirpath).joinpath(f)
             for dirpath, dirnames, filenames in os.walk(str(directory))
             for f in filenames if Path(f).suffix in extensions)
    return files


class DraftError(Exception):
    """Raised when attempting to create a Content subclass from a draft

    DraftError should be raised when:
        * A post's date is in the future
        * 'draft' appears on a line by itself in the file's metadata header
    """
    pass


class Content(object):
    """Base class for content"""
    def __init__(self, *, title, body, settings,
                 slug=None, source_path=None, **kwargs):
        """Initialise Content

        title:          str
        body:           str
        settings:       ConfigParser
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

    def __lt__(self, other):
        """Compare self with other based on title and slug

        Slugs are compared if titles are the same.
        Both checks are case-insensitive.
        """
        if self.title.lower() != other.title.lower():
            return self.title.lower() < other.title.lower()
        else:
            return self.slug.lower() < other.slug.lower()

    def __str__(self):
        """Return str(self)

        Format used:
            Title: path to source file
        """
        return '{0}: {1}'.format(
            self.title,
            self.source_path if self.source_path is not None else 'No path')

    @property
    def html(self):
        """Render self.body markdown text as HTML

        Uses the extensions stored in the config file under [markdown] as
        a whitespace-separated list under the 'extensions' property

        'markdown.extensions.' is added to members of the extension list
        that are missing it
        """
        if not hasattr(self, '_html'):
            prefix = 'markdown.extensions.'
            extensions = [
                ext if ext.startswith(prefix) else prefix + ext
                for ext in self.settings['markdown']['extensions'].split()
                ]
            md = markdown.Markdown(extensions=extensions)
            self._html = md.convert(self.body)
        return self._html

    @classmethod
    def from_file(class_, file, settings):
        """Parse file into an object of type class_

        class_:     the class from which the class method was called
        file:       a pathlib.Path
        settings:   a ConfigParser object containing the site's settings

        Raises DraftError if the file is explicitly marked as a draft,
        by way of 'draft' appearing by itself on a line in the metadata
        header.
        """
        with file.open() as f:
            # Split on first blank line
            meta, body = f.read().split('\n\n', maxsplit=1)
        body = body.strip('\n')

        # Split on first colon
        meta = [line.split(':', maxsplit=1) for line in meta.splitlines()]

        # Strip whitespace from keys and values
        meta = [[s.strip() for s in sublist] for sublist in meta]

        # Lowercase keys
        for sublist in meta:
            sublist[0] = sublist[0].lower()

        if ['draft'] in meta:
            raise DraftError('Marked draft in metadata header')

        return class_(body=body, settings=settings, source_path=file,
                      **dict(meta))

    @property
    def _path_part(self):
        """Not Implemented

        On subclasses, return the content's path part as str for use
        in directory paths and urls.

        Property should fetch template from settings, format and then
        store the result at _path_part_str so it can simply be returned
        in the future.

        Specifically:
            http://example.com/path/part.html
            output_root_dir/path/part.html
        """
        raise NotImplementedError()

    @property
    def output_path(self):
        """Path to Content's output file"""
        if not hasattr(self, '_output_path'):
            output_dir = Path(self.settings['paths']['output root'])
            self._output_path = output_dir.joinpath(self._path_part)
        return self._output_path

    @output_path.setter
    def output_path(self, value):
        """Override output_path by setting it directly"""
        self._output_path = value

    @property
    def url(self):
        """Content's URL"""
        if not hasattr(self, '_url'):
            site_url = self.settings['site']['url']
            self._url = urljoin(site_url, self._path_part)
        return self._url

    @url.setter
    def url(self, value):
        """Override url by setting it directly"""
        self._url = value


class Page(Content):
    """A Content subclass representing a static page

    Page is largely just a concrete version of Content, with the stub
    methods implemented.
    """
    @property
    def _path_part(self):
        """Path part of Page's output_path and url as a str

        Property fetches template from settings, formats and then stores
        the result so it can be simply returned in the future.

        Specifically:
            http://example.com/path/part.html
            output_root_dir/path/part.html
        """
        if not hasattr(self, '_path_part_str'):
            template = self.settings['paths']['page path template']
            self._path_part_str = template.format(content=self)
        return self._path_part_str


class Post(Content):
    """A Content subclass representing a blog post"""
    def __init__(self, *, title, body, date, settings,
                 slug=None, source_path=None, **kwargs):
        """Initialise Post

        For most parameters, see the Content docstring

        date:   datetime or str

        If date is a str, it is parsed into a datetime object using the
        format defined in the config files.
        """
        super().__init__(title=title, body=body, settings=settings,
                         slug=slug, source_path=source_path, **kwargs)
        if isinstance(date, str):
            date_format = settings['dates']['format']
            date = datetime.strptime(date, date_format)
        tz = pytz.timezone(settings['dates']['timezone'])
        date = tz.localize(date)
        if date > tz.localize(datetime.now()):
            # Post date is in the future and considered a draft
            raise DraftError('Date is in the future')
        self.date = date

    def __lt__(self, other):
        """Compare self with other based on date

        If self and other have identical dates, use superclass's
        implementation to test titles and slugs.
        """
        if self.date != other.date:
            return self.date < other.date
        else:
            return super().__lt__(other)

    def __str__(self):
        """Return str(self)

        Format used:
            %Y-%m-%d Title: path to source file
        """
        return '{0:%Y-%m-%d} {1}: {2}'.format(
            self.date, self.title,
            self.source_path if self.source_path is not None else 'No path')

    @property
    def _path_part(self):
        """Path part of Post's output_path and url as a str

        Property fetches template from settings, formats and then stores
        the result so it can be simply returned in the future.

        Specifically:
            http://example.com/path/part.html
            output_root_dir/path/part.html
        """
        if not hasattr(self, '_path_part_str'):
            template = self.settings['paths']['post path template']
            self._path_part_str = template.format(content=self)
        return self._path_part_str


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


def jinja_environment(templates_dir, settings, jinja_options=None):
    """Create a Jinja2 Environment with a loader for templates_dir

    settings:   ConfigParser of the site's settings
    options:    dictionary of custom options for the Jinja2 Environment
    """
    if jinja_options is None:
        jinja_options = {}
    opts = MAJESTIC_JINJA_OPTIONS.copy()    # get default options
    opts.update(jinja_options)              # update defaults with user options

    loader = jinja2.FileSystemLoader(str(templates_dir))
    env = jinja2.Environment(loader=loader, **opts)

    env.globals['settings'] = settings          # add settings as a global
    env.filters['rfc822_date'] = rfc822_date    # add custom filter

    return env


def load_jinja_options(settings):
    """Return the custom settings in templates root/jinja.json as a dict"""
    jinja_opts_filename = 'jinja.json'
    templates_root = Path(settings['paths']['templates root'])
    json_file = templates_root.joinpath(jinja_opts_filename)
    with json_file.open() as file:
        custom_options = json.load(file)
    return custom_options


def rfc822_date(date):
    """Return date in RFC822 format

    For reference, the format (in CLDR notation) is:
        EEE, dd MMM yyyy HH:mm:ss Z
    With the caveat that the weekday (EEE) and month (MMM) are always
    in English.

    Example:
        Sat, 19 Sep 2015 14:53:07 +0100

    For what it's worth, this doesn't strictly use the RFC822 date
    format, which is obsolete. (The current RFC of this type is 5322.)
    This should not be a problem — 822 calls for a two-digit year, and
    even the RSS 2.0 spec sample files (from 2003) use four digits.
    """
    weekday_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                   'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    weekday = weekday_names[date.weekday()]
    month = month_names[date.month - 1]
    template = '{weekday}, {d:%d} {month} {d:%Y %H:%M:%S %z}'
    return template.format(weekday=weekday, month=month, d=date)


def chunk(iterable, chunk_length):
    """Yield the members of its iterable chunk_length at a time

    If the length of the iterable is not a multiple of the chunk length,
    the final chunk contains the remaining data but does not fill to
    meet the chunk length (unlike the grouper recipe in the
    itertools documentation).
    """
    for idx in range(math.ceil(len(iterable) / chunk_length)):
        lower = idx * chunk_length
        upper = lower + chunk_length
        yield iterable[lower:upper]


class Index(object):
    """Index represents a blog index page

    It has the following attributes:
        page_number:    1 to len(index_pages)
        newer_index:    Index containing more recent posts or None
        older_index:    Index containing less recent posts or None
        output_path:    path the index should be written to (pathlib.Path)
        url:            url of the index (str)
        posts:          [Post] to be rendered on the index page

    An Index created with page_number 1 is always index.html.

    The class method .paginate_posts creates a list of Index objects out
    of a list of posts.
    """
    def __init__(self, page_number, posts, settings,
                 newer_index=None, older_index=None):
        """Initialise the Index and computer output_path and url"""
        self.page_number = page_number
        self.posts = posts
        self.settings = settings
        self.newer_index = newer_index
        self.older_index = older_index

        output_root = Path(settings['paths']['output root'])
        if page_number > 1:
            template = settings['paths']['index pages path template']
            path_part = template.format(index=self)
            self.url = urljoin(settings['site']['url'], path_part)
        else:
            path_part = 'index.html'
            self.url = settings['site']['url']
        self.output_path = output_root.joinpath(path_part)

    def __lt__(self, other):
        """Index compares by page_number"""
        return self.page_number < other.page_number

    def __str__(self):
        """Return str(self)"""
        template = 'Index page {page_number}, {num_posts} posts ({url})'
        return template.format(page_number=self.page_number,
                               num_posts=len(self.posts),
                               url=self.url)

    @classmethod
    def paginate_posts(class_, posts, settings):
        """Split up posts across a list of Index pages

        The returned list is ordered by index page number.
        """
        posts_per_page = settings.getint('index', 'posts per page')
        posts_newest_first = sorted(posts, reverse=True)
        chunked = chunk(posts_newest_first, chunk_length=posts_per_page)

        index_list = [Index(page_number=n, settings=settings, posts=post_list)
                      for n, post_list in enumerate(chunked, start=1)]

        for n, index_object in enumerate(index_list):
            if n != 0:                      # First index has the newest posts
                index_object.newer_index = index_list[n - 1]
            if n + 1 < len(index_list):     # Last index has the oldest posts
                index_object.older_index = index_list[n + 1]

        return index_list
