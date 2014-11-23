"""
Usage:
  python main.py URL [send]

Options:

  URL   some url, like http://example.com
  send  send a tweet (requires Twitter Oauth credentials)
"""
from __future__ import unicode_literals

from os import environ as env
import logging
import re
import sys

from pymarkovchain import MarkovChain
import project_runpy
import requests
import tweepy

from walk import walk


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
if not len(logger.handlers):
    # keep me from repeatedly adding this handler in ipython
    logger.addHandler(project_runpy.ColorizingStreamHandler())


def build_comments(url):
    if url[-1] != '/':
        url += '/'
    page = requests.get(url)
    content_type = page.headers['Content-Type']
    if 'application/rss' in content_type:
        from rss import rss
        return rss(page)
    return walk(page)


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
        # TODO yeah, this logic is stupid. I know.
        is_valid = True
        if text[0] == u'-':
            logger.warn('Starts with a hyphen: {}'.format(text))
            is_valid = False
        elif not re.search(r'\w', text):
            logger.warn('Not a real tweet: {}'.format(text))
            is_valid = False
        elif len(text) > 140:
            logger.warn(u'Too Long: {}'.format(text))
            is_valid = False
        if not is_valid:
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
    logger.info(u'Sent: {}'.format(text))


def do_something(host):
    comments = build_comments(host)
    cleaned = list(clean_comments(comments))

    if len(cleaned) < 20:
        # if we don't have enough comments, leave
        logger.error('Not enough comments on {}, only got {} ({}), needed 20'
            .format(host, len(cleaned), len(comments)))
        return

    mc = MarkovChain('/tmp/temp.db')
    mc.db = {}  # HACK to clear any existing data, we want to stay fresh
    mc.generateDatabase(
        # seems silly to join and then immediately split, but oh well
        '\n'.join(cleaned),
        sentenceSep='[\n]',
    )
    if 'send' in sys.argv:
        send_tweet(get_tweet_text(mc))
    else:
        print get_tweet_text(mc)
        # put stuff in global for debugging
        globals().update({
            'mc': mc,
            'comments': comments,
            'cleaned': cleaned,
            'host': host,
        })


if __name__ == '__main__':
    do_something(sys.argv[1])
