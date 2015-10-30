def process(*, posts, pages, settings):
    """Dummy process function that sets an attribute on each object"""
    for post in posts:
        post.test_attr = 'post'
    for page in pages:
        page.test_attr = 'page'
    return {'posts': posts, 'pages': pages}
