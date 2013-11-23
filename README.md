## Installation

If you don't have `virtualenv` or `pip` installed:

    $ sudo easy_install pip
    $ sudo pip install virtualenv

Once you have `virtualenv`:

    $ git clone <goopy>
    $ cd goopy
    $ virtualenv venv
    $ source venv/bin/activate
    $ pip install -r requirements.txt

Now scrape the example keywords:

    $ ./goo.py -vf example-keywords.txt

See the help message for usage:

    $ ./goo.py -h
