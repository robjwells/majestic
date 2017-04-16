#!/usr/bin/env python3

from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
import os
from pathlib import Path
import sys
import tempfile
import webbrowser

from docopt import docopt
import pytz

from majestic.utils import load_extensions
from majestic.content import Page, Post, DraftError
from majestic.collections import Archives, Index, RSSFeed, Sitemap
from majestic.resources import copy_resources
from majestic.templating import jinja_environment
from majestic.extensions import ExtensionStage, apply_extensions

__version__ = '0.2.0'

MAJESTIC_DIR = Path(__file__).resolve().parent


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
