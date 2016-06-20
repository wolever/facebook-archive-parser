facebook-archive-parser
=======================

A fast parser for Facebook's data archive, written in Python and PyPy
compatible.

Currently supports parsing messages and exporting them to TSV.

Archive download instructions: https://www.facebook.com/help/131112897028467/


Usage
-----

Exporting messages to TSV::

    $ pypy fbarchive.py archive/html/messages.html
    ...
    299k messages exported in 53s:
        archive/html/messages-text.tsv
        archive/html/messages-threads.tsv
        archive/html/messages-users.tsv

Messages are split into three files (formatted here for readability):

``messages-text.tsv``::

    thread_id   user_id timestamp               text
    0           0       2014-11-02T21:17:00     "what?"
    0           1       2014-11-02T21:17:00     "(Now I'm wondering\u2026"
    0           1       2014-11-02T21:17:00     "yea, I can imagine"
    ...

``messages-threads.tsv``::

    thread_name         thread_id
    David, Jane         0
    Ted, Jenny, David   1
    ...

``messages-users.tsv``::

    user_name   user_id
    Jane        0
    David       1
    Ted         2
    ...


These files can be loaded and joined with Pandas::

    >>> import pandas as pd
    >>> import ujson # ujson is significantly faster than stdlib's json
    >>> messages = pd.read_csv(
    ...    "messages-text.tsv", sep="\t", quoting=3,
    ...    parse_dates=[2], converters={3: ujson.loads},
    ... )
    >>> threads = pd.read_csv("messages-threads.tsv", sep="\t", index_col=1)
    >>> users = pd.read_csv("messages-users.tsv", sep="\t", index_col=1)
    >>> messages\
    ...    .join(users.user_name, on="user_id")\
    ...    .join(threads.thread_name, on="thread_id")\
    ...    .head(3)
    thread_id  user_id              timestamp                 text  user_name  thread_name
    0          0        0 2014-11-02 21:17:00                what?       Jane  David, Jane
    0          1        0 2014-11-02 21:17:00  (Now I'm wondering…      David  David, Jane
    0          1        0 2014-11-02 21:17:00   yea, I can imagine      David  David, Jane


Parsing is done in two phases because loading the HTML file can be quite slow
with cPython, but using Jupyter Notebook, Pandas, and Matplotlib can be
difficult or impossible from PyPy.
