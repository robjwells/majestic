#!/usr/bin/env python3

from datetime import datetime
from enum import Enum
from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
import os
from pathlib import Path
import sys
import tempfile
import webbrowser

from docopt import docopt
import jinja2
import pytz

from majestic.utils import load_extensions, absolute_urls
from majestic.content import Page, Post, DraftError
from majestic.collections import Archives, Index, RSSFeed, Sitemap
from majestic.resources import copy_resources

__version__ = '0.2.0'

MAJESTIC_DIR = Path(__file__).resolve().parent


class ExtensionStage(Enum):
    """Enum for the extension processing stages

    This enumeration is used to select an extension's processing
    function - one that operates on all pages and posts (regardless
    of what is actually going to be written to disk) and one that
    operates on all objects that will be written to disk (called
    objects_to_write in the process_blog function), normally
    including all index pages and archives.

    The processing function's name for each stage is stored as the
    corresponding member's value.
    """
    posts_and_pages = 'process_posts_and_pages'
    objects_to_write = 'process_objects_to_write'


def apply_extensions(*, modules, stage, settings,
                     pages=None, posts=None, objects=None):
    """Transform content with each module's process functions

    Keyword arguments must be used, and the following are mandatory:
        modules:        A list of imported python modules.
        stage:          An ExtensionStage enum member.
                        This sets which processing function is called.
        settings:       dictionary containing the site's settings.

    At the ExtensionStage.posts_and_pages stage, the following arguments
    should be provided:
        posts:          List of Post objects
        pages:          List of Page objects

    At the ExtensionStage.posts_and_pages stage, the following argument
    should be provided:
        objects:        List of BlogObject subclass instances.
                        This is the list of objects that will be
                        rendered and written to disk.

    Extensions are called in name order.

    Extensions should implement either or both of:
        module.process_posts_and_pages
        module.process_objects_to_write

    module.process_posts_and_pages is called with the following arguments:
        pages:          List of Page objects.
        posts:          List of Post objects.
        settings:       dictionary containing the site's settings.

    And should return a dictionary optionally containing any of
    the following keys:
        pages
        posts
        new_objects

    When used in the process_blog function, pages and posts should be a
    transformed list of the corresponding content type which replaces
    the existing list.

    If either are omitted, the existing list for each type is used. (So
    if you want to clear out the list for posts or pages, return an empty
    list under the corresponding key.)

    new_objects should be a list of BlogObject-compatible objects
    which will be appended to the existing objects_to_write list, and
    written to disk in the same way as everything else. So if an extension
    wants to write extra files, the author doesn't have to worry about
    constructing a jinja environment (etc) and writing to disk themselves.

    module.process_objects_to_write is called with the following arguments:
        objects:        list of BlogObjects
        settings:       dictionary containing the site's settings

    And should return a dictionary containing the following key:
        objects

    When used in the process_blog function, the list returned under the
    objects key is used to replace the list of BlogObjects that will
    be written to disk.
    """
    modules = sorted(modules, key=lambda m: m.__name__)
    process_func_name = stage.value
    process_functions = [getattr(m, process_func_name) for m in modules
                         if hasattr(m, process_func_name)]

    if stage is ExtensionStage.posts_and_pages:
        extra_objs = []
        for func in process_functions:
            processed = func(settings=settings, posts=posts[:], pages=pages[:])
            posts = processed['posts'] if 'posts' in processed else posts
            pages = processed['pages'] if 'pages' in processed else pages
            extra_objs.extend(processed.get('new_objects', []))
        return_dict = {'posts': posts, 'pages': pages,
                       'new_objects': extra_objs}
    elif stage is ExtensionStage.objects_to_write:
        for func in process_functions:
            objects = func(settings=settings, objects=objects[:])['objects']
        return_dict = {'objects': objects}

    return return_dict


def jinja_environment(user_templates, settings):
    """Create a Jinja2 Environment with a loader for templates_dir

    user_templates:    path to user templates directory
    settings:          dictionary of the site's settings

    The majestic default templates directory is also included in
    the returned Environment's template search path.
    """
    options = settings['jinja']

    default_templates = MAJESTIC_DIR.joinpath('default_templates')
    loader = jinja2.FileSystemLoader(
        map(str, [user_templates, default_templates]))  # order is important
    env = jinja2.Environment(loader=loader, **options)

    env.globals['settings'] = settings            # add settings as a global
    env.filters['rfc822_date'] = rfc822_date      # add custom filter
    env.filters['absolute_urls'] = absolute_urls  # add custom filter

    return env


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
                    if type(settings[key]) == dict:
                        settings[key].update(from_file[key])
                    elif type(settings[key]) == list:
                        settings[key].extend(from_file[key])
                else:
                    settings[key] = from_file[key]
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
    files = (Path(dirpath, f)
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


def process_blog(*, settings, write_only_new=True,
                 posts=True, pages=True, index=True, archives=True,
                 rss=True, sitemap=True, extensions=True):
    """Create output files from the blog's source

    By default, create the entire blog. Certain parts can
    be disabled by setting their corresponding parameter
    to False.

    By default, only Pages and Posts that are considered new (by
    checking content.is_new) are written out. This can be overridden
    by passing False to write_only_new.

    Sitemap can be created by itself but will raise if the first index,
    or any of the page or post output files don't exist. This is because
    the sitemap depends on knowing the mtime of those files on disk.

    If extensions is False, posts and pages are not processed with any
    extension modules present in the extensions directory.
    """
    content_dir = Path(settings['paths']['content root'])
    posts_dir = content_dir.joinpath(settings['paths']['posts subdir'])
    pages_dir = content_dir.joinpath(settings['paths']['pages subdir'])

    env = jinja_environment(
        user_templates=settings['paths']['templates root'],
        settings=settings
        )

    post_filenames = markdown_files(posts_dir)
    page_filenames = markdown_files(pages_dir)

    posts_list = []
    pages_list = []
    for class_, file_list, obj_list in [(Post, post_filenames, posts_list),
                                        (Page, page_filenames, pages_list)]:
        for fn in file_list:
            try:
                obj_list.append(class_.from_file(fn, settings))
            except DraftError:
                print('{file} is marked as a draft'.format(file=fn),
                      file=sys.stderr)

    posts_list.sort(reverse=True)
    pages_list.sort()

    objects_to_write = []

    extensions_loaded = False
    if extensions:
        extensions_dir = Path(settings['paths']['extensions root'])
        if extensions_dir.exists():
            modules = load_extensions(extensions_dir)
            extensions_loaded = True
            processed = apply_extensions(
                modules=modules, stage=ExtensionStage.posts_and_pages,
                pages=pages_list, posts=posts_list, settings=settings)
            posts_list = processed['posts']
            pages_list = processed['pages']
            objects_to_write.extend(processed['new_objects'])

    content_objects = []
    if posts:
        content_objects.extend(posts_list)
    if pages:
        content_objects.extend(pages_list)
    if write_only_new:
        content_objects = [c for c in content_objects if c.is_new]
    objects_to_write.extend(content_objects)

    if index:
        indexes = Index.paginate_posts(posts=posts_list, settings=settings)
        objects_to_write.extend(indexes)

    if archives:
        objects_to_write.append(Archives(posts=posts_list, settings=settings))

    if rss:
        objects_to_write.append(RSSFeed(posts=posts_list, settings=settings))

    if extensions_loaded:
        processed = apply_extensions(
            modules=modules, stage=ExtensionStage.objects_to_write,
            objects=objects_to_write, settings=settings)
        objects_to_write = processed['objects']

    for obj in objects_to_write:
        obj.render_to_disk(environment=env,
                           build_date=datetime.now(tz=pytz.utc),
                           all_posts=posts_list, all_pages=pages_list)

    if sitemap:
        if index:
            front_page = indexes[0]
        else:
            # Create dummy front so the sitemap can be generated by itself
            front_page = Index(page_number=1, posts=[], settings=settings)
            if not Index.output_path.exists():
                Index.output_path.touch()
        content_list = posts_list + pages_list + [front_page]
        sitemap = Sitemap(content=content_list, settings=settings)
        sitemap.render_to_disk(environment=env)


def main(argv):
    """Implements the command-line interface"""
    usage = '''\
Majestic - a simple static blog generator

Usage:
    majestic [options]
    majestic preview [--port=PORT] [options]
    majestic (-h | --help)
    majestic --version

Options:
    -h, --help              Display this help message.
    --version               Display the program version.

    -d DIR, --blog-dir=DIR  Path to blog directory. [default: .]
    -f, --force-write       Write all files no matter the modification date.

    -p PORT, --port=PORT    Port on which to start the preview server.
                            [default: 8451]

    -s CFG, --settings=CFG  Use the specified settings file.
    --no-defaults           Ignore Majestic's default settings.
    --no-locals             Ignore settings.cfg in BLOG_DIR.

    --skip-posts            Don't create post HTML files.
    --skip-pages            Don't create page HTML files.
    --skip-index            Don't create index page HTML files.
    --skip-archives         Don't create archives HTML file.
    --skip-rss              Don't create an RSS feed XML file.
    --skip-sitemap          Don't create a sitemap XML file.

    --no-extensions         Disable extensions.

    --no-resources          Don't place resources in output directory.
    --link-resources        Symlink resources instead of copying.
                            Preview always uses symlinks (unless
                            --no-resources is given).
    '''
    args = docopt(doc=usage, argv=argv, version=__version__)

    # Ensure the working directory is the blog directory
    os.chdir(args['--blog-dir'])

    # Load settings, including any specified custom config file
    if args['--settings'] is not None:
        custom_config = [args['--settings']]
    else:
        custom_config = None
    settings = load_settings(default=not args['--no-defaults'],
                             local=not args['--no-locals'],
                             files=custom_config)

    # Modify settings to allow preview server
    if args['preview']:
        # URLs under our control should be relative
        settings['site']['url'] = '/'
        temp_dir = tempfile.TemporaryDirectory()
        settings['paths']['output root'] = temp_dir.name
        # Symlink resources instead of copying
        args['--link-resources'] = True

    # Invert --skip-* options in args
    # A bit unwieldy, but better than having skip_* params to process_blog
    process_options = {k[7:]: not v for k, v in args.items()
                       if k.find('--skip-') != -1}

    # Set whether extensions should be used (same logic as skipping)
    process_options['extensions'] = not args['--no-extensions']

    process_blog(settings=settings,
                 write_only_new=not args['--force-write'],
                 **process_options)

    if not args['--no-resources']:
        copy_resources(settings=settings,
                       use_symlinks=args['--link-resources'])

    # Change to temp directory and start web server
    if args['preview']:
        os.chdir(temp_dir.name)
        port = int(args['--port'])
        url = 'http://localhost:{0}'.format(port)
        httpd = HTTPServer(
            server_address=('', port),
            RequestHandlerClass=SimpleHTTPRequestHandler)
        try:
            print('Starting Majestic preview server at {0}'.format(url),
                  file=sys.stderr)
            webbrowser.open(url)
            httpd.serve_forever()
        except KeyboardInterrupt:
            print('Shutting down webserver.', file=sys.stderr)
            httpd.socket.close()
            temp_dir.cleanup()
