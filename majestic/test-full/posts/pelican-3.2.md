title: Pelican 3.2 released
date: 2013-04-24
slug: pelican-3.2-released

Today we are pleased to announce the release of Pelican 3.2. Highlights of the
improvements contained in this release follow below.

For those who are new to Pelican, please refer to the `Getting Started Guide
<http://docs.getpelican.com/en/latest/getting_started.html>`_. There is also a
`Tutorials <https://github.com/getpelican/pelican/wiki/Tutorials>`_ page
available, which currently includes a link to a Pelican installation
screencast.

Highlights
==========

Python 3 support
----------------

As noted in `Pelican's Unified Codebase
<http://blog.getpelican.com/pelicans-unified-codebase.html>`_, this new version
of Pelican includes support for Python 3. All tests currently pass on Python
3.2, and we expect the same for Python 3.3 in the near future. (Pelican
interacts with a number of third-party components that have not yet been
fully updated for Python 3.3 compatibility.)

Override page save-to location from meta-data
---------------------------------------------

Instead of blog or a site with dated articles, some people want to use Pelican
to publish sites with non-chronological content. Pelican 3.2 enables this by
providing a way to override the save-to location from within a page's
meta-data, so for example, you can have a ``pages/index.md`` file that will
replace your site root's ``index.html``.

Time period archives
--------------------

For folks who use date-based URL schemes such as ``/2013/04/23/my-post/``,
you can now create per-year and per-month archives that will appear at
``/2013/`` and ``/2013/04/``, respectively.

Posterous blog import
---------------------

With Posterous shutting down on April 30th, this release offers the timely
ability to import an existing Posterous blog. There are only a few days
remaining, so if you have a Posterous blog and want to import it into a
Pelican-powered site, please act quickly!

Separate Pelican plugins repository
-----------------------------------

Pelican plugins have been moved out of the core Pelican repository and into
their `own repository <https://github.com/getpelican/pelican-plugins>`_.
This allows us to focus on the Pelican core while simultaneously encouraging
the community to extend Pelican's functionality in the form of modular plugins.

Refactoring, fixes, and improvements
------------------------------------

There have been a large number of improvements under the hood. While not an
exhaustive list, the `Pelican 3.2 milestone issues
<https://github.com/getpelican/pelican/issues?milestone=4&state=closed>`_
should provide a good overview of the many enhancements that are part of this
release.

Upgrade notes
=============

While we do everything we can to maximize backwards compatibility and ensure
smooth Pelican upgrades, it's possible that you may encounter un-anticipated
wrinkles. Following are a few notes that may help:

* Add ``from __future__ import unicode_literals`` near the top of your settings
  file.

* As noted above, Pelican plugins are now located in their own repository. If
  you currently use any plugins bundled with Pelican 3.1.1 or earlier, you
  should follow the instructions located in the `Pelican plugins repository
  <https://github.com/getpelican/pelican-plugins>`_ to re-enable those
  plugins.

* Document-relative URL generation is now off by default. If you previously
  relied on this feature and fully understand its potential disadvantages,
  you can re-enable it by adding ``RELATIVE_URLS = True`` to your settings
  file.

* The CSS class generated by the reST and Markdown processors was unified into
  a single ``highlight`` class. If you find that your code syntax highlighting
  has disappeared after upgrading, ensure that any instances of ``codehilite``
  in your CSS are replaced with ``highlight``.

* Support for Python 2.6 has been dropped as of Pelican 3.2. For those running
  on distros that do not have a more recent version of Python available, one
  possible solution is to compile Python 2.7.x and use it from within a
  virtualenv (e.g., via ``virtualenv -p $HOME/bin/python2.7 pelican``).

We will keep the above list updated with any additional items as we find them.

Special thanks
==============

As evidenced by our growing THANKS file, there were many people who
contributed to this release. A few folks deserve special mention for the
many hours they put into this new version of Pelican:

`Dirk Makowski <http://parenchym.com/pymblog/>`_ added support for Python 3,
including provisional ports for third-party components such as Typogrify and
SmartyPants.

`W. Trevor King <http://blog.tremily.us/>`_ has undertaken a significant
refactoring of the Pelican core, improving a wide swath of the codebase that
will continue to surface in future versions of Pelican.

`Deniz Turgut (Avaris) <http://avar.is/>`_ contributed so many features and
fixes to this release that it would be silly to even try to list them. He's put
so much work into Pelican that one of the maintainers insisted that he set up a
`Gittip profile <https://www.gittip.com/avaris/>`_ (which Deniz did under much
duress), to which an anonymous donor has already made a sizeable contribution.
If you want to thank Deniz for his hard work, please consider doing the same.
It would be great to see him on the "Top Receivers" list next week!

Staying in touch
================

2013 has been a busy year so far, as evidenced by both the number of commits
to Pelican as well as the lack of updates here on the Pelican blog.  (^_^)
We'll do our best to post more frequently in the months to come, both here on
the blog and also via the
`@getpelican Twitter account <http://twitter.com/getpelican>`_.