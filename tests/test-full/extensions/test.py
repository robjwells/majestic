import majestic


def process_posts_and_pages(*, posts, pages, settings):
    """Dummy process function that sets an attribute on each object"""
    for post in posts:
        post.test_attr = 'post'
    for page in pages:
        page.test_attr = 'page'

    new_page = majestic.Page(title='extension test', body='',
                             slug='extension-test', settings=settings)
    new_page.test_attr = 'page'     # Make it like every other page

    return {'posts': posts, 'pages': pages, 'new_objects': [new_page]}


def process_objects_to_write(*, objects, settings):
    new_page = majestic.Page(title='', body='', slug='objects_to_write',
                             settings=settings)
    return {'objects': objects + [new_page]}
