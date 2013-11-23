#!/usr/bin/env python
"""
Scrape the number of Google search results for given keywords

Usage:
  goo.py [-v|-vv|-q] [options] (KEYWORD...)
  goo.py [-v|-vv|-q] [options] (-f FILE)
  goo.py -h|--help|--version

Arguments:
  FILE      input file containing keywords, one per line

Options:
  --version  show version
  -h --help  display this help message
  -v         verbose mode (use -vv for debug output)
  -q         quiet mode (disables summary)
  -y         dry run, no requests are made and no files are written
  -a         append output to OUTFILE instead of overwriting
  -f --infile INFILE      input file. each line is considered a keyword
  -o --outfile OUTFILE    output file. if not set, results will be written to the console
  -d --delim DELIM        delimiter [default: ,]
  -w --wait SECONDS       minimum wait before processing the next keyword [default: 5]
  -z --wait-fuzz SECONDS  add randomness to wait times [default: 5]
  -t --template TEMPLATE  template string, substituting '%s' with the current keyword [default: %s]
  -l --language LANG      language setting passed as ?hl=LANG query parameter [default: en]
  -s --site DOMAIN        tld used for search url [default: com]

"""
__author__ = 'obartley'

import os
import sys
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
from natsort import natsorted
# settings globals
# note: these are used as variables to contain arguments that have been validated!
# some arguments are not validated and will not have corresponding settings globals!
arguments = {}
min_wait = 0    # seconds
max_wait = 0    # seconds
infile = ""
outfile = ""
outmode = 'w+'
delim = ","
template = ""
lang = ""
site = ""
dry_run = False

url_template = "https://www.google.%s/search?hl=%s&q=%s"
non_numeric = re.compile(r'[^\d]+')
numeric = re.compile(r'([0-9]+)')
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
        if not dry_run:
            soup = BeautifulSoup(html, 'html5lib')
            stats = soup.find(id='resultStats').contents[0]
            stats = non_numeric.sub('', stats)
            log.debug("resultStats=%s" % stats)
            return keyword, stats
        else:
            log.debug("resultStats=-1")
            return keyword, '-1'
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
    search_term = template % elem
    url = url_template % (arguments['--site'], arguments['--language'], urllib.quote_plus(search_term.encode('utf-8')))
    log.debug("fetching '%s' with user agent '%s'" % (url, user_agent))
    if not dry_run:
        req = urllib2.Request(url)
        req.add_header("User-Agent", user_agent)
        return urllib2.build_opener().open(req).read()



def do_wait():
    """
    sleep a random number of seconds between min_ and max_wait
    """
    s = random.randint(min_wait, max_wait)
    log.debug("waiting for %d seconds..." % s)
    for i in range(s):
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
            sys.stderr.write("total running time: %s\n" % datetime.timedelta(milliseconds=end - start))
        return result
    return wrapper


@elapsed
def main():
    if infile:
        with open(infile) as f:
            data = [l.strip().decode('utf-8') for l in f.readlines()]
    else:
        data = arguments['KEYWORD']

    user_agents = UserAgents()

    for i, element in enumerate(data):
        log.info("processing [%d/%d]: '%s'" % (i + 1, len(data), data[i]))
        data[i] = process(data[i], user_agents.next())
        if i + 1 != len(data):
            do_wait()

    log.debug("sorting results")

    data = natsorted(data, itemgetter(1))
    data.reverse()

    if outfile:
        try:
            log.info("writing results to %s" % os.path.abspath(outfile))
            if not dry_run:
                with open(outfile, outmode) as f:
                    for result in data:
                        f.write(('%s\n' % delim.join(result)).encode('utf-8'))
        except Exception as e:
            log.error("console dump due to error writing '%s' (%s)" % (outfile, str(e)))
            pp = pprint.PrettyPrinter()
            pp.pprint(data)
    else:
        for result in data:
            print(delim.join(result)).encode('utf-8')

    if not arguments['-q']:
        errors = Counter(elem[1] for elem in data)['-1']
        sys.stderr.write("processed %d keyword(s) with %d error(s)\n" % (len(data), errors))


if __name__ == "__main__":
    # parse command line arguments and then call main()
    arguments = docopt(__doc__, version='goo.py version 20131122')

    if arguments['-v'] == 2:
        log.setLevel(logging.DEBUG)
    elif arguments['-v'] == 1:
        log.setLevel(logging.INFO)
    elif arguments['-q']:
        log.setLevel(logging.CRITICAL)

    if arguments['-v'] == 2:
        pp = pprint.PrettyPrinter(stream=sys.stderr)
        pp.pprint(arguments)

    min_wait = int(arguments['--wait'])
    if min_wait < 0:
        log.error("--wait must be a positive value")
        exit(-1)
    if int(arguments['--wait-fuzz']) >= 0:
        max_wait = min_wait + int(arguments['--wait-fuzz'])
    else:
        log.error("--wait-fuzz must be a positive value")
        exit(-1)

    if not arguments['KEYWORD']:
        infile = arguments['--infile']
        if not os.path.exists(infile):
            log.error("'%s' does not exist!" % infile)
            exit(-1)
    outfile = arguments['--outfile']

    delim = arguments['--delim']
    if not delim:
        log.error("--delim can't be an empty string!")
        exit(-1)

    if arguments['-a']:
        outmode = 'a+'

    template = arguments['--template']
    try:
        template_test = template % 'keyword'
    except TypeError as e:
        log.error("--template must contain exactly one occurrence of '%s'")
        exit(-1)

    dry_run = arguments['-y']

    main()