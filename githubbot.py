#!/usr/bin/env python

SERVER = 'irc.pirateirc.net'
CHANNELS = ["#ppau-pwg"]
NICKS = ("gitbot", "gitbot-", "gitbot`")

import lurklib
import json
import threading
from bottle import abort, request, app, static_file, run


class GithubBot(lurklib.Client, threading.Thread):
    def __init__(self, *args, **kwargs):
        lurklib.Client.__init__(self, *args, **kwargs)
        threading.Thread.__init__(self)

    def on_connect(self):
        for channel in CHANNELS:
            self.join_(channel)
    
    def run(self):
        self.mainloop()


bot = GithubBot(server=SERVER, nick=NICKS)
app = app()


def format_message(payload, commit):
    c = set()
    for fn in commit.get('added',[]):
        if '/' in fn:
            c.add(fn.rsplit('/', 1))
    
    o = {}
    o['branch'] = payload['ref'].split('/')[-1]
    o['author'] = commit['author']['name']
    o['repo'] = payload['repository']['name']
    o['rev'] = commit['id'][:8]
    o['file_count'] = len(commit.get('added', []))
    o['dir_count'] = len(c)
    o['msg'] = commit['message']
    o['url'] = commit['url']
    
    return "{repo}: {author} {branch} * {rev} / ({file_count} files in {dir_count} dirs): {msg} - {url}".format(**o)


@app.post('/')
def github_post():
    payload = json.loads(request.forms.get('payload'))

    for commit in payload['commits']:
        msg = format_message(payload, commit)
        for channel in CHANNELS:
            bot.privmsg(channel, msg)


if __name__ == '__main__':
    bot.start()
    run(app, server="cherrypy", host='0.0.0.0', port='16667')
