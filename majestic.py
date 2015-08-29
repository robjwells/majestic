#!/usr/bin/env python

import configparser
import datetime
import pathlib

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
