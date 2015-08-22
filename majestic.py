#!/usr/bin/env python

import configparser
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
    def __init__(self, title, body, meta=None):
        """Initialise Page

        title:  str, required
        body:   str, required
        meta:   dict, optional
        """
        if title is None:
            raise ValueError('title cannot be None')
        if body is None:
            raise ValueError('body cannot be None')
        if meta is None:
            meta = {}

        self.title = title
        self.body = body
        self.meta = meta
