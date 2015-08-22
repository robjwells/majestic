#!/usr/bin/env python

import configparser
import datetime
import pathlib

MAJESTIC_DIR = pathlib.Path(__file__).resolve().parent


def load_settings(default=True, local=True, files=None):
    """Load specified config files or the default and local ones

    config_files:   a list of filenames [str]
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
        * mkdown
        * markdown
    """
    extensions = {'.md', '.mkd', '.mkdown', '.markdown'}
    return (file for file in dir.iterdir() if file.suffix in extensions)


class Page(object):
    """Basic content object with a title, body and optional metadata"""
    def __init__(self, title, body, **kwargs):
        """Initialise Page

        title:  str, required
        body:   str, required
        meta:   dict, optional
        """
        if title is None:
            raise ValueError('title cannot be None')
        if body is None:
            raise ValueError('body cannot be None')

        self.title = title
        self.body = body
        self.meta = kwargs


class Post(Page):
    """Content object representing a blog post

    Has all the attributes of Page (title, body, meta) but
    with the addition of a slug (for the URL) and a date
    """
    def __init__(self, title, body, slug, date, **kwargs):
        """Initialise Post

        title:  str, required
        body:   str, required
        slug:   str, required
        date:   datetime, required
        meta:   dict, optional
        """
        super().__init__(title=title, body=body, **kwargs)
        if slug is None:
            raise ValueError('slug cannot be None')
        if not isinstance(date, datetime.datetime):
            raise ValueError('date must be a datetime.datetime object')
        self.slug = slug
        self.date = date
