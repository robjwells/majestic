def process_posts_and_pages(*, posts, pages, settings):
    """Dummy processer that sets an attribute on posts and pages"""
    for post in posts:
        post.test_attr = 'post'
    for page in pages:
        page.test_attr = 'page'
    return {'posts': posts, 'pages': pages}

def process_objects_to_write(*, objects, settings):
    """Dummy processer that sets an attribute on all objects"""
    for obj in objects:
        obj.test_attr = 'obj'
    return {'objects': objects}
