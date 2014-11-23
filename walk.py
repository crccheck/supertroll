from __future__ import unicode_literals

import logging

from lxml import html
import project_runpy
import requests


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
if not len(logger.handlers):
    # keep me from repeatedly adding this handler in ipython
    logger.addHandler(project_runpy.ColorizingStreamHandler())


def walk(host):
    """Walk through a homepage looking for comment pages."""
    page = requests.get(host + '/')
    tree = html.fromstring(page.text)

    comment_links = tree.xpath("//a[@class='comments']/@href")

    all_comments = []
    links_retrieved = set()

    for link in comment_links:
        if link in links_retrieved:
            logger.info('Skipping {}'.format(link))
            continue
        links_retrieved.add(link)
        logger.info('Retrieving {}'.format(link))
        try:
            page = requests.get(host + link, timeout=2)
        except requests.Timeout as e:
            logger.warn(e)
            # just skip this one. who cares.
            continue
        tree = html.fromstring(page.text)
        # this may be splitting comments into multiples if there are line
        # breaks, but oh well
        comments = tree.xpath("//p[@class='comment']/text()")

        # cast to a standard type isntead of lxml.etree._ElementStringResult
        comments = map(unicode, comments)

        all_comments.extend(comments)
    return all_comments
