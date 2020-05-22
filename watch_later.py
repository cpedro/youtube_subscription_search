#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File: watch_later.py
Description: Searches YouTube subscriptions for new videos (since last run),
    and adds any new videos to 'Water Later' playlist.
"""

__author__ = 'Chris Pedro'
__copyright__ = '(c) Chris Pedro 2020'
__licence__ = 'MIT'
__version__ = '0.0.1'


import argparse
import dateutil.parser
import googleapiclient.discovery
import googleapiclient.errors
import json
import os
import pickle
import sys

from datetime import datetime, timedelta, timezone
from google_auth_oauthlib.flow import InstalledAppFlow
from signal import signal, SIGINT


# Files used to save states between runs.
credentials_file = 'client_credentials'
last_run_file = 'client_last_run'
subs_file = 'client_subscriptions'

# Delay (period in seconds) might be needed to avoid too API calls too quickly.
delay = 1

# If last_run doesn't exist, sent this may days ago to default value.
days_ago = 3


def load_credentials():
    with open(credentials_file, 'rb') as fp:
        return pickle.load(fp)


def save_crendentials(credentials):
    with open(credentials_file, 'wb') as fp:
        pickle.dump(credentials, fp, pickle.HIGHEST_PROTOCOL)


def load_last_run():
    if os.path.isfile(last_run_file):
        with open(last_run_file, 'rb') as fp:
            last_run = pickle.load(fp)
    else:
        last_run = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return last_run


def save_last_run():
    with open(last_run_file, 'wb') as fp:
        pickle.dump(datetime.now(timezone.utc), fp, pickle.HIGHEST_PROTOCOL)


def load_subscriptions():
    with open(subs_file, 'rb') as fp:
        return pickle.load(fp)


def save_subscriptions(subs):
    with open(subs_file, 'wb') as fp:
        pickle.dump(subs, fp, pickle.HIGHEST_PROTOCOL)


def authenticate(secrets_file):
    api_service_name = 'youtube'
    api_version = 'v3'
    scopes = ['https://www.googleapis.com/auth/youtube']

    """Try and load credentials if they've been saved. Else, auth and save them
    for next time."""
    try:
        credentials = load_credentials()
    except FileNotFoundError:
        flow = InstalledAppFlow.from_client_secrets_file(secrets_file, scopes)
        credentials = flow.run_console()
        save_crendentials(credentials)

    return googleapiclient.discovery.build(
        api_service_name, api_version, credentials=credentials)


def get_playlist_by_name(client, name):
    request = client.channels().list(
        part='contentDetails',
        mine=True)
    channel_info = request.execute()
    playlists = channel_info['items'][0]['contentDetails']['relatedPlaylists']
    return playlists[name]


def get_subs(client, **kwargs):
    if 'refresh_subs' not in kwargs or not kwargs['refresh_subs']:
        try:
            return load_subscriptions()
        except FileNotFoundError:
            pass

    max_results = 50
    nextPage = ''
    subs = []

    # First get all subscriptions.
    while True:
        request = client.subscriptions().list(
            part='snippet,contentDetails',
            pageToken=nextPage,
            maxResults=max_results,
            mine=True)
        sub_list = request.execute()

        subs.extend(sub['snippet'] for sub in sub_list['items'])

        try:
            nextPage = sub_list['nextPageToken']
        except BaseException:
            break

    # Next loop through subs and get their public playlists.
    for sub in subs:
        request = client.channels().list(
            part='contentDetails',
            id=sub['resourceId']['channelId'])
        channel_info = request.execute()
        content_details = channel_info['items'][0]['contentDetails']
        sub['playlists'] = content_details['relatedPlaylists']

    save_subscriptions(subs)
    return subs


def get_channel_uploads(client, channel):
    # Only get the last 10 uploads.
    max_results = 10

    request = client.playlistItems().list(
        part='contentDetails',
        maxResults=max_results,
        playlistId=channel['playlists']['uploads'])
    uploads = request.execute()
    return uploads['items']


def add_video_to_playlist(client, video_id, playlist):
    request = client.playlistItems().insert(
        part='snippet',
        body={
            'snippet': {
                'playlistId': playlist,
                'position': 0,
                'resourceId': {
                    'kind': 'youtube#video',
                    'videoId': video_id
                }
            }
        }
    )
    return request.execute()


def parse_args(args):
    """Parse command line arguments.
    """
    parser = argparse.ArgumentParser(description='YouTube Subscription Search')
    parser.add_argument(
        '-s', '--secrets-file', default='client_id.json',
        help='Client secret file.  See README.md on how to get this file.')
    parser.add_argument(
        '-r', '--refresh-subscriptions', action='store_true',
        help='Force a refresh of subscriptions.')
    parser.add_argument(
        '-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument(
        '-d', '--debug', action='store_true', help='Debug output')
    return parser.parse_args(args)


def main(args):
    """Main method.
    """
    args = parse_args(args)
    last_run = load_last_run()

    client = authenticate(args.secrets_file)
    subs = get_subs(client, refresh_subs=args.refresh_subscriptions)

    if args.debug:
        print(json.dumps(subs))

    if args.verbose:
        print('Last run: {}'.format(last_run.strftime('%Y-%m-%d %H:%M:%S%Z')))
        print('Searching {} channels for new videos.'.format(len(subs)))
        print('==========================================================')

    new_videos = []
    for channel in subs:
        if args.verbose:
            print('Searching {}.'.format(channel['title']))
        uploads = get_channel_uploads(client, channel)
        channel_videos = []

        if args.debug:
            print(json.dumps(uploads))

        for video in uploads:
            details = video['contentDetails']
            published = dateutil.parser.isoparse(details['videoPublishedAt'])
            # Give 1 hour as a bit of a buffer to last run.
            if published > last_run - timedelta(hours=1):
                channel_videos.append(details)

        if args.verbose:
            print('- Found {} videos to be added.'.format(len(channel_videos)))

        new_videos.extend(channel_videos)

    if args.debug:
        print(json.dumps(new_videos))

    if len(new_videos):
        if args.verbose:
            print('==========================================================')
            print('Adding {} videos to Watch Later'.format(len(new_videos)))

        added = 0
        skipped = 0
        for video in new_videos:
            try:
                add_video_to_playlist(client, video['videoId'], 'WL')
                added += 1
            except googleapiclient.errors.HttpError:
                skipped += 1

        if args.verbose:
            print('==========================================================')
            print(('{} videos added.\n'
                   '{} videos already in the playlist.').format(
                added, skipped))
    elif args.verbose:
        print('==========================================================')
        print('No Videos to add.')

    save_last_run()


def handler(signal_received, frame):
    """Signal handler. Allows ^C to interupt cleanly.
    """
    sys.exit(0)


if __name__ == '__main__':
    signal(SIGINT, handler)
    sys.exit(main(sys.argv[1:]))

