#!/usr/bin/env python

import configparser
import pathlib

MAJESTIC_DIR = pathlib.Path(__file__).resolve().parent

def load_settings(config_files=None):
    """Load specified config files or the default and local ones

    config_files:   a list of filenames [str]
    """
    if config_files is None:
        default_cfg = MAJESTIC_DIR.joinpath('majestic.cfg')
        local_cfg = pathlib.Path.cwd().joinpath('settings.cfg')
        config_files = map(str, [default_cfg, local_cfg])
    config = configparser.ConfigParser()
    config.read(config_files)
    return config
