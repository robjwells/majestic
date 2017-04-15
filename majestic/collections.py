from datetime import datetime

import pytz

from majestic.content import BlogObject
from majestic.utils import chunk


class PostsCollection(BlogObject):
    """Base class for a collection of posts

    This should be subclassed for objects that work on several posts,
    such as for indexes and archives.

    Apart from the settings object, it takes only one argument on
    initialisation: a collection of post that is stored newest-first
    (the collection is sorted in reverse order).
    """
    def __init__(self, posts, settings):
        self._settings = settings
        self.posts = sorted(posts, reverse=True)

    def __iter__(self):
        """Iterate over self.posts"""
        return (post for post in self.posts)


class Index(PostsCollection):
    """Index represents a blog index page

    It has the following attributes:
        page_number:        1 to len(index_pages)
        newer_index_url:    url to an index with more recent posts or None
        older_index_url:    url to an index with less recent posts or None
        output_path:        path the index should be written to (pathlib.Path)
        url:                url of the index (str)
        posts:              [Post] to be rendered on the index page

    An Index created with page_number 1 is always saved to a file named
    index.html and its url is the site's url.

    The class method .paginate_posts creates a list of Index objects out
    of a list of posts.
    """
    _path_template_key = 'index pages path template'
    _template_file_key = 'index'

    def __init__(self, page_number, posts, settings,
                 newer_index_url=None, older_index_url=None):
        """Initialise the Index and computer output_path and url"""
        super().__init__(posts=posts, settings=settings)

        self.page_number = page_number
        self.newer_index_url = newer_index_url
        self.older_index_url = older_index_url

        if page_number == 1:
            self.path_part = 'index.html'           # Override for output path
            self.url = settings['site']['url']      # Set as plain url

    def __iter__(self):
        """Iterate over self.posts"""
        return (post for post in self.posts)

    def __eq__(self, other):
        """Compare self with other based on content attributes"""
        attrs = ['page_number', 'posts', 'output_path', 'url',
                 'newer_index_url', 'older_index_url']
        return all(getattr(self, a) == getattr(other, a) for a in attrs)

    def __lt__(self, other):
        """Index compares by page_number"""
        return self.page_number < other.page_number

    def __str__(self):
        """Return str(self)"""
        template = 'Index page {page_number}, {num_posts} posts ({url})'
        return template.format(page_number=self.page_number,
                               num_posts=len(self.posts),
                               url=self.url)

    @classmethod
    def paginate_posts(class_, posts, settings):
        """Split up posts across a list of index pages

        The returned list is ordered by index page number.
        """
        posts_per_page = settings['index']['posts per page']
        posts_newest_first = sorted(posts, reverse=True)
        chunked = chunk(posts_newest_first, chunk_length=posts_per_page)

        index_list = [class_(page_number=n, settings=settings, posts=post_list)
                      for n, post_list in enumerate(chunked, start=1)]

        for n, index_object in enumerate(index_list):
            if n != 0:                      # First index has the newest posts
                index_object.newer_index_url = index_list[n - 1].url
            if n + 1 < len(index_list):     # Last index has the oldest posts
                index_object.older_index_url = index_list[n + 1].url

        return index_list


class RSSFeed(PostsCollection):
    """An RSS feed for a blog"""
    _path_template_key = 'rss path template'
    _template_file_key = 'rss'

    def __init__(self, posts, settings):
        """Initialise RSSFeed with a list of posts and the site settings

        posts can be any list of posts, and only the most recent n are
        stored as a posts attribute on the object. The number chosen
        is set in the settings file under [rss][number of posts].

        The superclass's __init__ isn't called because the posts list
        has to be sorted before being limited, so there's no point
        calling super().__init__ and doing unnecessary work.
        """
        self._settings = settings
        post_limit = settings['rss']['number of posts']
        self.posts = sorted(posts, reverse=True)[:post_limit]


class Archives(PostsCollection):
    """An archives page for a blog

    Should be initialised with all of the blog's posts.
    """
    _path_template_key = 'archives path template'
    _template_file_key = 'archives'


class Sitemap(BlogObject):
    """Represents an XML sitemap

    Contains a list of tuples [(str, datetime)] that correspond to the
    url (loc) and modification date (lastmod) of each sitemap entry.

    The modification date is the file's modification time in UTC, as an
    aware datetime. This skips around issues of retrieving the system
    timezone (not a trivial task and of no advantage) yet allows the
    inclusion of a timezone in the sitemap itself.
    """
    _path_template_key = 'sitemap path template'
    _template_file_key = 'sitemap'

    def __init__(self, content, settings):
        """Initialise Sitemap with site settings and a list of BlogObjects

        content:    [BlogObject] containing each file to be represented
        """
        self._settings = settings
        self.url_date_pairs = []
        for file in content:
            url = file.url
            mtime = file.output_path.stat().st_mtime
            mod_date = datetime.fromtimestamp(mtime, tz=pytz.utc)
            self.url_date_pairs.append((url, mod_date))

    def __iter__(self):
        """Iterate over the tuples in self.url_date_pairs"""
        return (item for item in self.url_date_pairs)
