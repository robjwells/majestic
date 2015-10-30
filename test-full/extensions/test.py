import majestic

def process(*, posts, pages, settings):
    """Dummy process function that sets an attribute on each object"""
    for post in posts:
        post.test_attr = 'post'
    for page in pages:
        page.test_attr = 'page'

    new_page = majestic.Page(title='extension test', body='',
                             slug='extension-test', settings=settings)
    new_page.test_attr = 'page'     # Make it like every other page

    return {'posts': posts, 'pages': pages, 'objects_to_write': [new_page]}
