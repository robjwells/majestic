import markdown

MD_INSTANCE = None


def get_markdown(settings, reload=False):
    """Return a customised markdown.Markdown instance

    The returned instance will be set up with any extensions specified
    in the settings dictionary.
    """
    global MD_INSTANCE
    if MD_INSTANCE is None or reload:
        MD_INSTANCE = markdown.Markdown(
            extensions=settings['markdown']['extensions'].keys(),
            extension_configs=settings['markdown']['extensions']
            )
    return MD_INSTANCE


def _reset_cached_markdown():
    global MD_INSTANCE
    MD_INSTANCE = None
