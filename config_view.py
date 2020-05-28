#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File: config_view.py
Description: Prints out the youtube_subscription_search configuraiton in JSON.
"""


__author__ = 'Chris Pedro'
__copyright__ = '(c) Chris Pedro 2020'
__licence__ = 'MIT'


import json
import os
import pickle
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

    with open(settings.subs_file, 'rb') as fp:
        print(json.dumps({
            'configuration': 'Subscriptions',
            'config_file': settings.subs_file,
            'subscriptions': pickle.load(fp)}))


def handler(signal_received, frame):
    """Signal handler. Allows ^C to interupt cleanly.
    """
    sys.exit(0)


if __name__ == '__main__':
    signal(SIGINT, handler)
    sys.exit(main(sys.argv[1:]))

