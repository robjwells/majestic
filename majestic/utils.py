import importlib
import re
import string
import sys

from unidecode import unidecode


def load_extensions(directory):
    """Import all modules in directory and return a list of them"""
    # Add extensions directory to path
    sys.path.insert(0, str(directory))

    module_names = [file.stem for file in directory.iterdir()
                    if file.suffix == '.py']
    imported_modules = [importlib.import_module(name) for name in module_names]

    # Remove extensions directory from path
    sys.path = sys.path[1:]
    return imported_modules


def validate_slug(slug):
    """Test slug for validity and return a boolean

    Slugs containing any characters other than those in the unreserved
    set according to IETF RFC 3986 are deemed to be invalid. Other
    than percent-encoded characters, the acceptable characters are:

    a-z A-Z 0-9 - . _ ~

    Note that only ASCII alphabetic characters are allowed. (Covered by
    the inclusive ranges 0x41-0x5A and 0x61-0x7A.)

    Slugs containing a percent character that is not followed by
    two hex digits are also deemed to be invalid.

    The use of capital letters, periods, underscores and tildes in slugs
    is acceptable but discouraged.
    """
    good_chars = set(string.ascii_letters + string.digits + '-._~' + '%')
    hex_set = set(string.hexdigits)

    is_empty_string = len(slug) == 0
    contains_bad_chars = bool(set(slug) - good_chars)

    contains_bad_percent = False
    for match in re.finditer(r'%(.{,2})', slug):
        encoded = match.group(1)
        if len(encoded) < 2 or not set(encoded).issubset(hex_set):
            contains_bad_percent = True
    return not (is_empty_string or contains_bad_chars or contains_bad_percent)


def normalise_slug(slug):
    """Rewrite slug to contain only valid characters

    Valid characters are deemed to be:

    a-z 0-9 -

    Any other characters (including percent encoded characters)
    are removed from the output. Note that this function is more
    strict with the characters it emits than validate_slug is
    with the characters that it accepts.

    Spaces are changed to hyphens.

    This function borrows heavily from Dr Drang's post ASCIIfying:
    http://www.leancrew.com/all-this/2014/10/asciifying/
    """
    separators = re.compile(r'[—–/:;,.~_]')
    percent_enc = re.compile(r'%[0-9a-f]{2}')
    not_valid = re.compile(r'[^- a-z0-9]')  # Spaces handled separately
    hyphens = re.compile(r'-+')

    new_slug = slug.lower()
    new_slug = separators.sub('-', new_slug)
    new_slug = percent_enc.sub('-', new_slug)
    new_slug = unidecode(new_slug)
    new_slug = not_valid.sub('', new_slug)
    new_slug = new_slug.replace(' ', '-')
    new_slug = hyphens.sub('-', new_slug)
    new_slug = new_slug.strip('-')

    if not new_slug:
        raise ValueError('Slug is the empty string')

    return new_slug
