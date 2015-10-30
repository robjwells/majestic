def process(*, posts, pages, settings):
    """Dummy process function that sets an attribute on each object"""
    for post in posts:
        post.test_attr = True
    return {'posts': posts}
