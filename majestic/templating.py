from pathlib import Path
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
import jinja2


MAJESTIC_DIR = Path(__file__).resolve().parent


def absolute_urls(html, base_url):
    """Change relative URLs in html to absolute URLs using base_url

    Arguments:
        html:           str containing HTML markup
        base_url:       str containing a URL
    """
    parsed_html = BeautifulSoup(html, 'html.parser')
    for attr in ['href', 'src', 'poster']:
        for tag in parsed_html.select('[{0}]'.format(attr)):
            tag_url = tag[attr]
            if not urlparse(tag_url).netloc:
                tag[attr] = urljoin(base_url, tag_url)
    return str(parsed_html)


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
