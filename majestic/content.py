from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

import pytz

import majestic.md as md
from majestic.utils import normalise_slug, validate_slug


class DraftError(Exception):
    """Raised when attempting to create a Content subclass from a draft

    DraftError should be raised when:
        * A post's date is in the future
        * 'draft' appears on a line by itself in the file's metadata header
    """
    pass


class ModificationDateError(Exception):
    """Raised by Content.is_new if modification_date is None"""
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
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        with self.output_path.open(mode='w') as file:
            file.write(rendered_html)


class Content(BlogObject):
    """Base class for content"""
    def __init__(self, *, title, body, settings,
                 slug=None, source_path=None, save_as=None,
                 modification_date=None, **kwargs):
        """Initialise Content

        title:                  str
        body:                   str
        settings:               dictionary
        slug:                   str (if not None)
        source_path:            pathlib.Path (if not None)
        save_as:                str (if not None)
        modification_date:      datetime.datetime (if not None)

        If slug is None, a slug is created from title.

        source_path can be None to allow programmatic Content creation
        kwargs used to create metadata container self.meta.

        save_as overrides the location to which the content is written,
        affecting both the output_path and url.

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

        if save_as is not None:
            self.path_part = save_as

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

        Uses the extensions listed in the config file under
        markdown -> extensions. The dictionary key names are used as
        strings to import the extensions and the dictionary contents
        as the extension configuration.
        """
        if not hasattr(self, '_html'):
            self._html = md.get_markdown(self._settings).convert(self.body)
        return self._html

    @classmethod
    def from_file(class_, file, settings):
        """Parse file into an object of type class_

        class_:     the class from which the class method was called
        file:       a pathlib.Path
        settings:   a dictionary containing the site's settings

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
    def is_new(self):
        """Return True if source file is newer than output file

        Compares self.modification_time to self.output_path's st_mtime.
        Returns True if the output file does not exist.

        is_new raises if output_path exists but modification_date is None.
        (This will only happen through programmatic Content creation when
        neither source_path or modification_date are provided at init.)
        """
        if not hasattr(self, '_is_new'):
            if not self.output_path.exists():
                return True
            if self.modification_date is None:
                raise ModificationDateError('modification_date is None')
            output_timestamp = self.output_path.stat().st_mtime
            output_date = datetime.fromtimestamp(output_timestamp)
            self._is_new = self.modification_date > output_date
        return self._is_new

    @is_new.setter
    def is_new(self, value):
        """Override _is_new by setting it directly"""
        self._is_new = value


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
