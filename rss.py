from __future__ import unicode_literals

from lxml import etree


def rss(page):
    """Gets comments from a rss feed."""
    page = etree.fromstring(page.content)
    return [x.text for x in page.xpath('//item/description')]
