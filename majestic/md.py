import markdown
from markdown.extensions import Extension
from pathlib import Path

from majestic.extensions import load_extensions

MD_INSTANCE = None


def load_custom_markdown_extensions(extensions_dir):
    """Return a list of custom markdown extension classes

    extensions_dir:    pathlib.Path
    """
    if not extensions_dir.exists():
        return []
    load_extensions(extensions_dir)
    return [e for e in Extension.__subclasses__()]


def get_custom_extensions(settings):
    """Instantiate custom markdown extensions with configuration"""
    classes = load_custom_markdown_extensions(
        Path(settings['paths']['extensions root']))
    instances = []
    for ext in classes:
        config = settings['markdown']['extensions'].pop(ext.__name__, {})
        instances.append(ext(**config))
    return instances


def get_markdown(settings, reload=False):
    """Return a customised markdown.Markdown instance

    The returned instance will be set up with any extensions specified
    in the settings dictionary.
    """
    global MD_INSTANCE
    if MD_INSTANCE is None or reload:
        extensions = [*get_custom_extensions(settings),
                      *settings['markdown']['extensions'].keys()]
        MD_INSTANCE = markdown.Markdown(
            extensions=extensions,
            extension_configs=settings['markdown']['extensions']
            )
    return MD_INSTANCE


def _reset_cached_markdown():
    global MD_INSTANCE
    MD_INSTANCE = None
