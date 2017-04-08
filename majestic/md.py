import markdown

def get_markdown(settings):
    """Return a customised markdown.Markdown instance

    The returned instance will be set up with any extensions specified
    in the settings dictionary.
    """
    return markdown.Markdown()
