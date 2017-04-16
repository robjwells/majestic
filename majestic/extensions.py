from enum import Enum
import importlib
import sys


class ExtensionStage(Enum):
    """Enum for the extension processing stages

    This enumeration is used to select an extension's processing
    function - one that operates on all pages and posts (regardless
    of what is actually going to be written to disk) and one that
    operates on all objects that will be written to disk (called
    objects_to_write in the process_blog function), normally
    including all index pages and archives.

    The processing function's name for each stage is stored as the
    corresponding member's value.
    """
    posts_and_pages = 'process_posts_and_pages'
    objects_to_write = 'process_objects_to_write'


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


def apply_extensions(*, modules, stage, settings,
                     pages=None, posts=None, objects=None):
    """Transform content with each module's process functions

    Keyword arguments must be used, and the following are mandatory:
        modules:        A list of imported python modules.
        stage:          An ExtensionStage enum member.
                        This sets which processing function is called.
        settings:       dictionary containing the site's settings.

    At the ExtensionStage.posts_and_pages stage, the following arguments
    should be provided:
        posts:          List of Post objects
        pages:          List of Page objects

    At the ExtensionStage.posts_and_pages stage, the following argument
    should be provided:
        objects:        List of BlogObject subclass instances.
                        This is the list of objects that will be
                        rendered and written to disk.

    Extensions are called in name order.

    Extensions should implement either or both of:
        module.process_posts_and_pages
        module.process_objects_to_write

    module.process_posts_and_pages is called with the following arguments:
        pages:          List of Page objects.
        posts:          List of Post objects.
        settings:       dictionary containing the site's settings.

    And should return a dictionary optionally containing any of
    the following keys:
        pages
        posts
        new_objects

    When used in the process_blog function, pages and posts should be a
    transformed list of the corresponding content type which replaces
    the existing list.

    If either are omitted, the existing list for each type is used. (So
    if you want to clear out the list for posts or pages, return an empty
    list under the corresponding key.)

    new_objects should be a list of BlogObject-compatible objects
    which will be appended to the existing objects_to_write list, and
    written to disk in the same way as everything else. So if an extension
    wants to write extra files, the author doesn't have to worry about
    constructing a jinja environment (etc) and writing to disk themselves.

    module.process_objects_to_write is called with the following arguments:
        objects:        list of BlogObjects
        settings:       dictionary containing the site's settings

    And should return a dictionary containing the following key:
        objects

    When used in the process_blog function, the list returned under the
    objects key is used to replace the list of BlogObjects that will
    be written to disk.
    """
    modules = sorted(modules, key=lambda m: m.__name__)
    process_func_name = stage.value
    process_functions = [getattr(m, process_func_name) for m in modules
                         if hasattr(m, process_func_name)]

    if stage is ExtensionStage.posts_and_pages:
        extra_objs = []
        for func in process_functions:
            processed = func(settings=settings, posts=posts[:], pages=pages[:])
            posts = processed['posts'] if 'posts' in processed else posts
            pages = processed['pages'] if 'pages' in processed else pages
            extra_objs.extend(processed.get('new_objects', []))
        return_dict = {'posts': posts, 'pages': pages,
                       'new_objects': extra_objs}
    elif stage is ExtensionStage.objects_to_write:
        for func in process_functions:
            objects = func(settings=settings, objects=objects[:])['objects']
        return_dict = {'objects': objects}

    return return_dict
