from os import environ as env
import logging
import re

from pymarkovchain import MarkovChain
from lxml import html
import project_runpy
import requests
import tweepy


HOST = 'http://www.texastribune.org'
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
if not len(logger.handlers):
    # keep me from repeatedly adding this handler in ipython
    logger.addHandler(project_runpy.ColorizingStreamHandler())


def build_comments(host=HOST):
    page = requests.get(HOST + '/')
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
            page = requests.get(HOST + link, timeout=2)
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


def clean_comments(comments):
    for comment in comments:
        if 'http' in comment:
            # throw away comments with urls
            continue
        if 'trib' in comment.lower():
            # throw away comments that might directly reference us (4th wall)
            continue
        # add a zero width space, \u200b, to keep mentions and hash tags out
        text = re.sub(r'([@#])(\w)', u'\\1\u200b\\2', comment)
        yield text


def get_tweet_text(mc):
    text = mc.generateString()
    for __ in range(10):  # only try 10 times
        if len(text) > 140:
            logger.warn(u'Too Long: {}'.format(text))
            text = mc.generateString()
    # FIXME if it can't find one, it'll return one too long anyways :(
    return text


def send_tweet(text):
    auth = tweepy.OAuthHandler(
            env.get('CONSUMER_KEY'), env.get('CONSUMER_SECRET'))
    auth.set_access_token(
            env.get('ACCESS_KEY'), env.get('ACCESS_SECRET'))
    api = tweepy.API(auth)
    api.update_status(text)


if __name__ == '__main__':
    comments = build_comments()
    cleaned = list(clean_comments(comments))

    if len(cleaned) > 20:  # minumum sample size

        mc = MarkovChain('/tmp/temp.db')
        mc.db = {}  # HACK to clear any existing data, we want to stay fresh
        mc.generateDatabase(
            # seems silly to join and then immediately split, but oh well
            '\n'.join(cleaned),
            sentenceSep='[\n]',
        )
        print get_tweet_text(mc)
