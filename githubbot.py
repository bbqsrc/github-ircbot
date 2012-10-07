#!/usr/bin/env python

import lurklib
import json
import requests
from threading import Thread
from queue import Queue
from bottle import abort, request, app, static_file, run


CONFIG = json.load(open('config.json'))
SERVER = CONFIG.get('server')
CHANNELS = CONFIG.get('channels')
NICKS = tuple(CONFIG.get('nicks'))
ALLOWED_IPS = CONFIG.get('allowed_ips')
DEBUG = CONFIG.get('debug', False)


class GithubBot(lurklib.Client, Thread):
    def __init__(self, *args, **kwargs):
        lurklib.Client.__init__(self, *args, **kwargs)
        Thread.__init__(self)
        self.q = Queue()
    
    def mainloop(self):
        while self.keep_going:
            with self.lock:
                if self.on_connect and not self.readable(2):
                    self.on_connect()
                    self.on_connect = None
                
                if not self.keep_going:
                    break
                
                try:
                    msg = self.q.get(False)
                    for channel in CHANNELS:
                        self.privmsg(channel, msg)
                except Exception as e:
                    pass

                self.process_once()

    def on_connect(self):
        for channel in CHANNELS:
            self.join_(channel)
    
    def run(self):
        self.mainloop()


bot = GithubBot(server=SERVER, nick=NICKS)
app = app()


def get_client_ip():
    x_forwarded_for = request.environ.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.environ.get('REMOTE_ADDR')
    return ip


def format_message(payload, commit):
    c = set()
    files = commit.get('added', []) + commit.get('modified', []) + commit.get('removed', [])
    for fn in ():
        if '/' in fn:
            c.add(fn.rsplit('/', 1))
    
    o = {}
    o['branch'] = payload['ref'].split('/')[-1]
    o['author'] = commit['author']['name']
    o['repo'] = payload['repository']['name']
    o['rev'] = commit['id'][:8]
    o['file_count'] = len(files)
    o['dir_count'] = len(c)+1
    o['msg'] = commit['message']

    response = requests.post("http://git.io", data={"url": commit['url']})
    if response.status_code in (201, 302) and response.headers['location']:
        o['url'] = response.headers['location']
    else:
        o['url'] = commit['url']

    return "{repo}: {author} {branch} * {rev} / ({file_count} files in {dir_count} dirs): {msg} - {url}".format(**o)


@app.post('/')
def github_post():
    payload = json.loads(request.forms.get('payload', {}))
    if get_client_ip() not in ALLOWED_IPS or payload == {}:
        return "Go away!"

    if DEBUG:
        print(payload)

    for commit in payload['commits']:
        msg = format_message(payload, commit)
        bot.q.put(msg)

if __name__ == '__main__':
    bot.start()
    run(app, server="cherrypy", host='0.0.0.0', port='16667')
