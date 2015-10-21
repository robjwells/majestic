#!/usr/bin/env python

from configparser import ConfigParser
from datetime import datetime
import json
import math
import os
from pathlib import Path
import re
import string
import sys
from textwrap import dedent
from urllib.parse import urljoin

from docopt import docopt
import jinja2
import markdown
import pytz
from unidecode import unidecode

MAJESTIC_DIR = Path(__file__).resolve().parent
MAJESTIC_JINJA_OPTIONS = {
    'auto_reload': False,
    }


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


def jinja_environment(user_templates, settings, jinja_options=None):
    """Create a Jinja2 Environment with a loader for templates_dir

    user_templates:    path to user templates directory
    settings:          ConfigParser of the site's settings
    options:           dictionary of custom options for the Jinja2 Environment

    The majestic default templates directory is also included in
    the returned Environment's template search path.
    """
    if jinja_options is None:
        jinja_options = {}
    opts = MAJESTIC_JINJA_OPTIONS.copy()    # get default options
    opts.update(jinja_options)              # update defaults with user options

    default_templates = MAJESTIC_DIR.joinpath('default_templates')
    loader = jinja2.FileSystemLoader(
        map(str, [user_templates, default_templates]))  # order is important
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


def load_settings(default=True, local=True, files=None):
    """Load config from standard locations and specified files

    default:    bool, load default config file
    local:      bool, load config file from current directory
    files:      list of filenames to load
    """
    if files is None:
        files = []
    if local:
        files.insert(0, Path.cwd().joinpath('settings.cfg'))
    if default:
        files.insert(0, MAJESTIC_DIR.joinpath('majestic.cfg'))
    settings = ConfigParser(interpolation=None, inline_comment_prefixes='#')
    settings.read(map(str, files))
    return settings


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
    files = (Path(dirpath).joinpath(f)
             for dirpath, dirnames, filenames in os.walk(str(directory))
             for f in filenames if Path(f).suffix in extensions)
    return files


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


class DraftError(Exception):
    """Raised when attempting to create a Content subclass from a draft

    DraftError should be raised when:
        * A post's date is in the future
        * 'draft' appears on a line by itself in the file's metadata header
    """
    pass


class ModificationDateError(Exception):
    """Raised by Content.is_new() if modification_date is None"""
    pass


class BlogObject(object):
    """Abstract base class for objects representing html/xml files

    Provides default implementations of common properties and a
    method for rendering the object on a template and writing
    it to disk.

    Public properties defined here:
        * URL
        * Output path
        * Rendering self to a file

    Concrete subclasses are required to define the following class
    variables:
        * _path_template_key
        * _template_file_key

    These are used in the inherited properties and method to retrieve
    options from an object's self._settings and are the way that
    subclasses customise their output file path, url and set their
    related jinja template.
    """
    @property
    def _path_template_key(self):
        """Key to retrieve the class's path template from settings

        Subclasses should implement this as a simple class variable.
        The implementation on BlogObject raises NotImplementedError.
        """
        message = 'Subclasses must define _path_template_key class variable'
        raise NotImplementedError(message)

    @property
    def _template_file_key(self):
        """Key to retrieve the class's template filename from settings

        Subclasses should implement this as a simple class variable.
        The implementation on BlogObject raises NotImplementedError.
        """
        message = 'Subclasses must define _template_file_key class variable'
        raise NotImplementedError(message)

    @property
    def path_part(self):
        """Path part of output_path and url as a str

        Property fetches template from settings, formats and then stores
        the result so it can be simply returned in the future.

        By path part, this is what's meant:
            http://example.com/[path/part.html]
            output_root_dir/[path/part.html]
        """
        if not hasattr(self, '_path_part'):
            template = self._settings['paths'][self._path_template_key]
            self._path_part = template.format(content=self)
        return self._path_part

    @path_part.setter
    def path_part(self, value):
        """Override path_part by setting it directly"""
        self._path_part = value

    @property
    def output_path(self):
        """Return path at which object should be written"""
        if not hasattr(self, '_output_path'):
            output_dir = Path(self._settings['paths']['output root'])
            self._output_path = output_dir.joinpath(self.path_part)
        return self._output_path

    @output_path.setter
    def output_path(self, value):
        """Override output_path by setting it directly"""
        self._output_path = value

    @property
    def url(self):
        """Return url at which object will be available on the web

        'index.html' is trimmed to allow for for clean URLs.
        """
        if not hasattr(self, '_url'):
            site_url = self._settings['site']['url']
            full = urljoin(site_url, self.path_part)
            if full.endswith('index.html'):
                full = full[:-len('index.html')]
            self._url = full
        return self._url

    @url.setter
    def url(self, value):
        """Override url by setting it directly"""
        self._url = value

    def render_to_disk(self, environment, **kwargs):
        """Render self with a jinja template and write to a file"""
        template = environment.get_template(
            self._settings['templates'][self._template_file_key])
        rendered_html = template.render(content=self, **kwargs)
        try:
            self.output_path.parent.mkdir(parents=True)
        except FileExistsError:
            pass
        with self.output_path.open(mode='w') as file:
            file.write(rendered_html)


class Content(BlogObject):
    """Base class for content"""
    def __init__(self, *, title, body, settings,
                 slug=None, source_path=None, modification_date=None,
                 **kwargs):
        """Initialise Content

        title:                  str
        body:                   str
        settings:               ConfigParser
        slug:                   str (if not None)
        source_path:            pathlib.Path (if not None)
        modification_date:      datetime.datetime (if not None)

        If slug is None, a slug is created from title.

        source_path can be None to allow programmatic Content creation
        kwargs used to create metadata container self.meta.

        modification_date can be provided explicitly, otherwise it is
        taken from the source file (or is None if neither are provided).

        modification_date is a naive datetime in the local time, as it's
        only used for internal comparisons (which only matter on the
        system on which majestic is run).
        """
        self.title = title
        self.body = body
        self._settings = settings
        if slug is None:
            slug = normalise_slug(title)
        elif not validate_slug(slug):
            slug = normalise_slug(slug)
        self.slug = slug
        self.source_path = source_path

        if modification_date is None and source_path is not None:
            mtime = source_path.stat().st_mtime
            modification_date = datetime.fromtimestamp(mtime)
        self.modification_date = modification_date

        self.meta = kwargs

    def __eq__(self, other):
        """Compare self with other based on content attributes"""
        if not isinstance(other, self.__class__):
            return NotImplemented
        attrs = ['title', 'slug', 'body', 'source_path', 'meta',
                 'output_path', 'url']
        return all(getattr(self, a) == getattr(other, a) for a in attrs)

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
                for ext in self._settings['markdown']['extensions'].split()
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

    def is_new(self):
        """Return True if source file is newer than output file

        Compares self.modification_time to self.output_path's st_mtime.
        Returns True if the output file does not exist.

        is_new raises if output_path exists but modification_date is None.
        (This will only happen through programmatic Content creation when
        neither source_path or modification_date are provided at init.)
        """
        if not self.output_path.exists():
            return True
        if self.modification_date is None:
            raise ModificationDateError('modification_date is None')
        output_date = datetime.fromtimestamp(self.output_path.stat().st_mtime)
        return self.modification_date > output_date


class Page(Content):
    """A Content subclass representing a static page

    Page is just a concrete version of Content, with the BlogObject
    key variables defined.
    """
    _path_template_key = 'page path template'
    _template_file_key = 'page'


class Post(Content):
    """A Content subclass representing a blog post"""
    _path_template_key = 'post path template'
    _template_file_key = 'post'

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
        if date > datetime.now(tz=pytz.utc):
            # Post date is in the future and considered a draft
            raise DraftError('Date is in the future')
        self.date = date

    def __eq__(self, other):
        """Compare self with other based on content attributes

        Here only the dates are compared, and the rest is
        delegated to the superclass's implementation
        """
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self.date == other.date and super().__eq__(other)

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


class PostsCollection(BlogObject):
    """Base class for a collection of posts

    This should be subclassed for objects that work on several posts,
    such as for indexes and archives.

    Apart from the settings object, it takes only one argument on
    initialisation: a collection of post that is stored newest-first
    (the collection is sorted in reverse order).
    """
    def __init__(self, posts, settings):
        self._settings = settings
        self.posts = sorted(posts, reverse=True)

    def __iter__(self):
        """Iterate over self.posts"""
        return (post for post in self.posts)


class Index(PostsCollection):
    """Index represents a blog index page

    It has the following attributes:
        page_number:        1 to len(index_pages)
        newer_index_url:    url to an index with more recent posts or None
        older_index_url:    url to an index with less recent posts or None
        output_path:        path the index should be written to (pathlib.Path)
        url:                url of the index (str)
        posts:              [Post] to be rendered on the index page

    An Index created with page_number 1 is always saved to a file named
    index.html and its url is the site's url.

    The class method .paginate_posts creates a list of Index objects out
    of a list of posts.
    """
    _path_template_key = 'index pages path template'
    _template_file_key = 'index'

    def __init__(self, page_number, posts, settings,
                 newer_index_url=None, older_index_url=None):
        """Initialise the Index and computer output_path and url"""
        super().__init__(posts=posts, settings=settings)

        self.page_number = page_number
        self.newer_index_url = newer_index_url
        self.older_index_url = older_index_url

        if page_number == 1:
            self.path_part = 'index.html'           # Override for output path
            self.url = settings['site']['url']      # Set as plain url

    def __iter__(self):
        """Iterate over self.posts"""
        return (post for post in self.posts)

    def __eq__(self, other):
        """Compare self with other based on content attributes"""
        attrs = ['page_number', 'posts', 'output_path', 'url',
                 'newer_index_url', 'older_index_url']
        return all(getattr(self, a) == getattr(other, a) for a in attrs)

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
        """Split up posts across a list of index pages

        The returned list is ordered by index page number.
        """
        posts_per_page = settings.getint('index', 'posts per page')
        posts_newest_first = sorted(posts, reverse=True)
        chunked = chunk(posts_newest_first, chunk_length=posts_per_page)

        index_list = [class_(page_number=n, settings=settings, posts=post_list)
                      for n, post_list in enumerate(chunked, start=1)]

        for n, index_object in enumerate(index_list):
            if n != 0:                      # First index has the newest posts
                index_object.newer_index_url = index_list[n - 1].url
            if n + 1 < len(index_list):     # Last index has the oldest posts
                index_object.older_index_url = index_list[n + 1].url

        return index_list


class RSSFeed(PostsCollection):
    """An RSS feed for a blog"""
    _path_template_key = 'rss path template'
    _template_file_key = 'rss'

    def __init__(self, posts, settings):
        """Initialise RSSFeed with a list of posts and the site settings

        posts can be any list of posts, and only the most recent n are
        stored as a posts attribute on the object. The number chosen
        is set in the settings file under [rss][number of posts].

        The superclass's __init__ isn't called because the posts list
        has to be sorted before being limited, so there's no point
        calling super().__init__ and doing unnecessary work.
        """
        self._settings = settings
        post_limit = settings.getint('rss', 'number of posts')
        self.posts = sorted(posts, reverse=True)[:post_limit]


class Archives(PostsCollection):
    """An archives page for a blog

    Should be initialised with all of the blog's posts.
    """
    _path_template_key = 'archives path template'
    _template_file_key = 'archives'


class Sitemap(BlogObject):
    """Represents an XML sitemap

    Contains a list of tuples [(str, datetime)] that correspond to the
    url (loc) and modification date (lastmod) of each sitemap entry.

    The modification date is the file's modification time in UTC, as a
    naive datetime. This skips around issues of retrieving the system
    timezone (not a trivial task and of no advantage).
    """
    _path_template_key = 'sitemap path template'
    _template_file_key = 'sitemap'

    def __init__(self, content, settings):
        """Initialise Sitemap with site settings and a list of BlogObjects

        content:    [BlogObject] containing each file to be represented
        """
        self._settings = settings
        self.url_date_pairs = []
        for file in content:
            url = file.url
            mtime = file.output_path.stat().st_mtime
            mod_date = datetime.fromtimestamp(mtime, tz=pytz.utc)
            self.url_date_pairs.append((url, mod_date))

    def __iter__(self):
        """Iterate over the tuples in self.url_date_pairs"""
        return (item for item in self.url_date_pairs)


def process_blog(*, settings, write_only_new=True,
                 posts=True, pages=True, index=True, archives=True,
                 rss=True, sitemap=True):
    """Create output files from the blog's source

    By default, create the entire blog. Certain parts can
    be disabled by setting their corresponding parameter
    to False.

    By default, only Pages and Posts that are considered new (by
    checking content.is_new()) are written out. This can be overridden
    by passing False to write_only_new.

    Sitemap can be created by itself but will raise if the first index,
    or any of the page or post output files don't exist. This is because
    the sitemap depends on knowing the mtime of those files on disk.
    """
    content_dir = Path(settings['paths']['content root'])
    posts_dir = content_dir.joinpath(settings['paths']['posts subdir'])
    pages_dir = content_dir.joinpath(settings['paths']['pages subdir'])

    if settings.getboolean('jinja', 'custom options'):
        jinja_opts = load_jinja_options(settings)
    else:
        jinja_opts = None

    env = jinja_environment(user_templates=settings['paths']['templates root'],
                            settings=settings, jinja_options=jinja_opts)

    post_filenames = markdown_files(posts_dir)
    page_filenames = markdown_files(pages_dir)
    posts_list = [Post.from_file(f, settings) for f in post_filenames]
    pages_list = [Page.from_file(f, settings) for f in page_filenames]
    posts_list.sort(reverse=True)
    pages_list.sort()

    objects_to_write = []

    content_objects = []
    if posts:
        content_objects.extend(posts_list)
    if pages:
        content_objects.extend(pages_list)
    if write_only_new:
        content_objects = [c for c in content_objects if c.is_new()]
    objects_to_write.extend(content_objects)

    if index:
        indexes = Index.paginate_posts(posts=posts_list, settings=settings)
        objects_to_write.extend(indexes)

    if archives:
        objects_to_write.append(Archives(posts=posts_list, settings=settings))

    if rss:
        objects_to_write.append(RSSFeed(posts=posts_list, settings=settings))

    for obj in objects_to_write:
        obj.render_to_disk(environment=env,
                           build_date=datetime.now(tz=pytz.utc),
                           all_posts=posts_list, all_pages=pages_list)

    if sitemap:
        # Create dummy front page so the sitemap can be generated by itself
        dummy_front_page = Index(page_number=1, posts=[], settings=settings)
        content_list = posts_list + pages_list + [dummy_front_page]
        sitemap = Sitemap(content=content_list, settings=settings)
        sitemap.render_to_disk(environment=env)
