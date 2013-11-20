#!/usr/bin/env python
"""
Scrape the number of Google search results for keywords in FILE and sort by highest number of results

Usage:
  goo.py [-q|-v|-vv] (FILE) [-a] [--outfile=OUTFILE|-o OUTFILE] [--delim=DELIM|-d DELIM] [--wait=WAIT|-w WAIT] [--wait-fuzz=FUZZ|-z FUZZ]
  goo.py -h | --help | --version

Arguments:
  FILE      input file containing keywords, one per line

Options:
  --version  show version
  -h --help  display this help message
  -v         verbose mode (use -vv for debug output)
  -q         quiet mode (disables summary)
  -a         append output to OUTFILE instead of overwriting
  -o --outfile OUTFILE    output file [default: ./output.txt]
  -d --delim DELIM        delimiter [default: ,]
  -w --wait SECONDS       minimum wait before processing the next keyword [default: 5]
  -z --wait-fuzz SECONDS  add randomness to wait times [default: 5]

"""
__author__ = 'obartley'

import os
import random
import time
import logging
import re
import urllib
import urllib2
import datetime
import pprint


from bs4 import BeautifulSoup
from docopt import docopt
from operator import itemgetter
from collections import Counter

min_wait = 0    # seconds
max_wait = 0    # seconds
infile = ""
outfile = ""
outmode = 'w+'
delim = ","
arguments = {}

url_template = "https://www.google.com/search?q=%s"
non_numeric = re.compile(r'[^\d]+')
logging.basicConfig()
log = logging.getLogger('goo.py')


class UserAgents:
    """
    Simple iterator that repeatedly cycles through available User Agent strings on calls to next()
    """
    def __init__(self):
        self.index = 0
        self.data = [
            "Mozilla/5.0 (Windows; U; Windows NT 5.1; de; rv:1.9.2.3) Gecko/20100401 Firefox/3.6.3",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_6_8) AppleWebKit/534.30 (KHTML, like Gecko) Chrome/12.0.742.112 Safari/534.30",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.8; rv:25.0) Gecko/20100101 Firefox/25.0",
            "Mozilla/5.0 (X11; Linux x86_64; rv:17.0) Gecko/20121202 Firefox/17.0 Iceweasel/17.0.1",
            "Mozilla/5.0 (Windows; U; MSIE 9.0; WIndows NT 9.0; en-US))",
            "w3m/0.5.2 (Linux i686; it; Debian-3.0.6-3)"
        ]

    def __iter__(self):
        return self

    def next(self):
        i = self.index
        self.index += 1
        if self.index == len(self.data):
            self.index = 0
        return self.data[i]


def process(keyword, user_agent):
    """
    Download search results and extract results stats
    """
    try:
        html = fetch_html(keyword, user_agent)
        soup = BeautifulSoup(html, 'html5lib')
        stats = soup.find(id='resultStats').contents[0]
        stats = non_numeric.sub('', stats)
        log.debug("resultStats=%s" % stats)
        results = (keyword, stats)
        return results
    except Exception as e:
        if arguments['-v'] == 2:
            log.exception("'%s' could not be processed" % keyword)
        else:
            log.error("'%s' could not be processed" % keyword)
        return keyword, '-1'  # we write the file expecting a string, not an int


def fetch_html(elem, user_agent):
    """
    Download the raw html of a search results page using the provided user agent string
    """
    url = url_template % urllib.quote_plus(elem.encode('utf-8'))
    log.debug("fetching '%s' with user agent '%s'" % (url, user_agent))
    req = urllib2.Request(url)
    req.add_header("User-Agent", user_agent)
    return urllib2.build_opener().open(req).read()


def do_wait():
    """
    sleep a random number of seconds between min_ and max_wait
    """
    s = random.randint(min_wait, max_wait)
    log.debug("waiting for %d seconds..." % s)
    for i in reversed(range(s)):
        time.sleep(1)


def elapsed(method):
    """
    Decorator function that displays the total running time of the decorated function
    """
    def wrapper(*args, **kw):
        start = int(round(time.time() * 1000))
        result = method(*args, **kw)
        end = int(round(time.time() * 1000))
        if not arguments['-q']:
            print("total running time: %s" % datetime.timedelta(milliseconds=end - start))
        return result
    return wrapper


@elapsed
def main():
    with open(infile) as f:
        data = [l.strip().decode('utf-8') for l in f.readlines()]

    user_agents = UserAgents()

    for i, element in enumerate(data):
        log.info("processing [%d/%d]: '%s'" % (i + 1, len(data), data[i]))
        data[i] = process(data[i], user_agents.next())
        if i + 1 != len(data):
            do_wait()

    log.debug("sorting results")
    data.sort(key=itemgetter(1), reverse=True)

    try:
        log.info("writing results to %s" % os.path.abspath(outfile))
        with open(outfile, outmode) as f:
            for result in data:
                f.write(('%s\n' % delim.join(result)).encode('utf-8'))
        if not arguments['-q']:
            errors = Counter(elem[1] for elem in data)['-1']
            print("processed %d keyword(s) with %d error(s)" % (len(data), errors))
    except Exception as e:
        log.error("console dump due to error writing '%s' (%s)" % (outfile, str(e)))
        pp = pprint.PrettyPrinter()
        pp.pprint(data)


if __name__ == "__main__":
    # parse command line arguments and then call main()
    arguments = docopt(__doc__, version='goo.py version 20131120')

    if arguments['-v'] == 2:
        log.setLevel(logging.DEBUG)
    elif arguments['-v'] == 1:
        log.setLevel(logging.INFO)
    elif arguments['-q']:
        log.setLevel(logging.CRITICAL)

    log.debug("log level=%s" % str(log.getEffectiveLevel()))

    min_wait = int(arguments['--wait'])
    if min_wait < 0:
        log.error("--wait must be a positive value")
        exit(-1)
    if int(arguments['--wait-fuzz']) >= 0:
        max_wait = min_wait + int(arguments['--wait-fuzz'])
    else:
        log.error("--wait-fuzz must be a positive value")
        exit(-1)
    log.debug("min_cooldown=%d, max_cooldown=%d" % (min_wait, max_wait))

    infile = arguments['FILE']
    if not os.path.exists(infile):
        log.error("'%s' does not exist!" % infile)
        exit(-1)
    outfile = arguments['--outfile']
    log.debug("infile: %s" % infile)
    log.debug("outfile: %s" % outfile)

    delim = arguments['--delim']
    if delim == '':
        log.error("--delim can't be an empty string!")
        exit(-1)
    log.debug("delim='%s'" % delim)
    if arguments['-a']:
        outmode = 'a+'
    log.debug("outmode='%s'" % outmode)

    main()