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
