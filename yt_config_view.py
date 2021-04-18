#!/usr/bin/env python3
# -*- encoding: utf-8; py-indent-offset: 4 -*-
"""
File: config_view.py
Description: Prints out the youtube_subscription_search configuraiton in JSON.
"""


__author__ = 'Chris Pedro'
__copyright__ = '(c) Chris Pedro 2020'
__licence__ = 'MIT'


import json
import pickle5 as pickle
import sys

from google.oauth2.credentials import Credentials
from signal import signal, SIGINT
from youtube_search import YouTubeSearch


def main(args):
    """Main method.
    """
    api = YouTubeSearch()
    settings = api.settings

    with open(settings.credentials_file, 'rb') as fp:
        credentials = pickle.load(fp)
        if isinstance(credentials, Credentials):
            print(json.dumps({
                'configuration': 'Credentials',
                'config_file': settings.credentials_file,
                'token': credentials.token,
                'expiry': str(credentials.expiry),
                '_scopes': credentials._scopes,
                '_id_token': credentials._id_token,
                '_token_uri': credentials._token_uri,
                '_client_id': credentials._client_id,
                '_client_secret': credentials._client_secret,
                '_quota_project_id': credentials._quota_project_id}))

    with open(settings.last_run_file, 'rb') as fp:
        last_run = {
            'configuration': 'Last Run',
            'config_file': settings.last_run_file}
        last_run.update(pickle.load(fp))
        last_run['last_run'] = last_run['last_run'].strftime(
            '%Y-%m-%d %H:%M:%S%Z')
        print(json.dumps(last_run))

    with open(settings.dest_pl_file, 'rb') as fp:
        dest_playlist = {
            'configuration': 'Destination Playlist',
            'config_file': settings.dest_pl_file}
        dest_playlist.update(pickle.load(fp))
        dest_playlist['last_update'] = dest_playlist['last_update'].strftime(
            '%Y-%m-%d %H:%M:%S%Z')
        print(json.dumps(dest_playlist))

    with open(settings.subs_file, 'rb') as fp:
        subs = {
            'configuration': 'Subscriptions',
            'config_file': settings.subs_file}
        subs.update(pickle.load(fp))
        subs['last_update'] = subs['last_update'].strftime(
            '%Y-%m-%d %H:%M:%S%Z')
        print(json.dumps(subs))


def handler(signal_received, frame):
    """Signal handler. Allows ^C to interrupt cleanly.
    """
    sys.exit(0)


if __name__ == '__main__':
    signal(SIGINT, handler)
    sys.exit(main(sys.argv[1:]))

