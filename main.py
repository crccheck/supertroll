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

import markovify
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
        yield comment


def send_tweet(text):
    auth = tweepy.OAuthHandler(
        env.get('CONSUMER_KEY'), env.get('CONSUMER_SECRET'))
    auth.set_access_token(
        env.get('ACCESS_KEY'), env.get('ACCESS_SECRET'))
    api = tweepy.API(auth)
    # add a zero width space, \u200b, to keep mentions and hash tags out
    text = re.sub(r'([@#])(\w)', u'\\1\u200b\\2', text)
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

    all_comments = '. '.join(comments)
    text_model = markovify.Text(all_comments)
    tweet_text = text_model.make_short_sentence(138)
    for __ in range(10):  # only try 10 times, yet again, this is stupid but I'm lazy
        if tweet_text in all_comments:
            # prevent script from sending something that's verbatim from comments
            logger.warn('Already said: {}'.format(tweet_text))
            tweet_text = text_model.make_short_sentence(138)
        else:
            # tweet is ok
            break
    if 'send' in sys.argv:
        send_tweet(tweet_text)
    else:
        print tweet_text
        # put stuff in global for debugging
        globals().update({
            'text_model': text_model,
            'comments': comments,
            'cleaned': cleaned,
            'host': host,
        })


if __name__ == '__main__':
    do_something(sys.argv[1])
