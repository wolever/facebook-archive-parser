import os
import sys
import json
import time
import argparse
from itertools import count
from datetime import datetime
from collections import defaultdict
from xml.etree.ElementTree import iterparse

class invalid_char_stripping_file(file):
    def read(self, *a, **kw):
        res = file.read(self, *a, **kw)
        return res.replace("\x10", " ").replace("\x03", " ")


def parse_messages(stream):
    """ Parses the messages from message file ``stream`` yielding triples of
        ``(user_map, thread_map, (thread_id, user_id, date, text))``. """

    usermap = defaultdict(count().next)
    threadmap = defaultdict(count().next)
    cur_user = None
    cur_date = None
    cur_thread = None
    msg_text = None
    msg_count = 0

    for event, elem in iterparse(stream, events=set(("start", "end"))):
        #span {'class': 'user'}
        #span {'class': 'meta'}
        cls = elem.attrib.get("class")
        #print event, elem.tag, cls, elem.text

        if event == "start" and (cls == "message" or elem.tag == "p"):
            if elem.tag == "p":
                msg_text = elem.text
            if cur_user is not None:
                assert cur_date, "bad date: %s (%s)" %(cur_date, msg_count)
                assert cur_thread is not None
                msg_count += 1
                if msg_text is None:
                    msg_text = ""
                #print cur_thread, cur_date, msg_text.encode("utf-8")
                yield (
                    usermap,
                    threadmap,
                    (cur_thread, usermap[cur_user], cur_date, msg_text),
                )
            cur_user = cur_date = msg_text = None
        elif event == "end":
            if cls == "user":
                cur_user = (elem.text or "").encode("ascii", "xmlcharrefreplace")
            elif cls == "meta":
                cur_date = elem.text and datetime.strptime(elem.text, "%A, %d %B %Y at %H:%M %Z")
        elif event == "start" and cls == "thread":
            cur_thread = threadmap[(elem.text or "").encode("ascii", "xmlcharrefreplace")]


def parse_and_write_messages(args):
    stream = invalid_char_stripping_file(args.archive_file)
    user_map = None
    thread_map = None

    outdir = args.output or os.path.dirname(args.archive_file)
    open_output = lambda *a: open(os.path.join(outdir, *a), "w")

    start_time = time.time()
    last_msg = time.time()
    with open_output("messages-text.tsv") as f:
        f.write("thread_id\tuser_id\ttimestamp\ttext\n")
        count = 0
        for user_map, thread_map, msg in parse_messages(stream):
            count += 1
            f.write("%s\t%s\t%s\t%s\n" %(
                msg[0],
                msg[1],
                msg[2].isoformat(),
                json.dumps(msg[3]),
            ))
            if count % 5000 == 0:
                now = time.time()
                if now - last_msg > 1:
                    last_msg = now
                    sys.stderr.write("\r%dk exported (%d msgs/sec)      " %(
                        count / 1000,
                        count / (now - start_time),
                    ))
                    sys.stderr.flush()

    sys.stderr.write("\r%dk messages exported in %ds (%d msgs/sec):\n" %(
        count / 1000,
        time.time() - start_time,
        count / (time.time() - start_time),
    ))

    sys.stderr.write("    %s\n" %(f.name, ))

    with open_output("messages-users.tsv") as f:
        f.write("user_name\tuser_id\n")
        for k, v in user_map.iteritems():
            f.write("%s\t%s\n" %(k, v))
        sys.stderr.write("    %s\n" %(f.name, ))

    with open_output("messages-threads.tsv") as f:
        f.write("thread_name\tthread_id\n")
        for k, v in thread_map.iteritems():
            f.write("%s\t%s\n" %(k, v))
        sys.stderr.write("    %s\n" %(f.name, ))


parser = argparse.ArgumentParser(description="Facebook Archive parser")
parser.add_argument("archive_file", help="""
    The archive file to parse. Currently only html/messages.html is supported.
""")
parser.add_argument("-o", "--output", default=None, help="""
    Output directory. By default, files are saved along side the archive file.
""")


if __name__ == "__main__":
    args = parser.parse_args()
    parse_and_write_messages(args)
