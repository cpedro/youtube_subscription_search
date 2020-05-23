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
__version__ = '0.0.2'


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
from pathlib import Path
from signal import signal, SIGINT


# YouTube API settings.
api_service_name = 'youtube'
api_version = 'v3'
scopes = ['https://www.googleapis.com/auth/youtube']

# Files used to save states between runs.
config_path = os.path.join(
    str(Path.home()), '.config', 'youtube_subscription_search')
credentials_file = os.path.join(config_path, 'credentials')
last_run_file = os.path.join(config_path, 'last_run')
subs_file = os.path.join(config_path, 'subscriptions')

# If last_run doesn't exist, set this many days ago to default value.
days_ago = 3
# Buffer for last_run to compare to new videos, in minutes.
last_run_buffer = 60


def load_credentials():
    """Load saved credentials from file.
    """
    with open(credentials_file, 'rb') as fp:
        return pickle.load(fp)


def save_crendentials(credentials):
    """Save credentials to file.
    """
    with open(credentials_file, 'wb') as fp:
        pickle.dump(credentials, fp, pickle.HIGHEST_PROTOCOL)


def load_last_run():
    """Load last run time from file.
    """
    try:
        with open(last_run_file, 'rb') as fp:
            last_run = pickle.load(fp)
    except FileNotFoundError:
        # If there is no last run, tell program it was X days ago.
        last_run = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return last_run


def save_last_run():
    """Save 'last run', which is just the current time to file.
    """
    with open(last_run_file, 'wb') as fp:
        pickle.dump(datetime.now(timezone.utc), fp, pickle.HIGHEST_PROTOCOL)


def load_subscriptions():
    """Load subscriptions from file.
    """
    with open(subs_file, 'rb') as fp:
        return pickle.load(fp)


def save_subscriptions(subs):
    """Save subscribers to file.
    """
    with open(subs_file, 'wb') as fp:
        pickle.dump(subs, fp, pickle.HIGHEST_PROTOCOL)


def authenticate(secrets_file):
    """Authenticate to YouTube.  This will try and load saved credentials first
    and if it's not successful it will prompt the user for access and save
    credentials for the next run.
    """
    try:
        credentials = load_credentials()
    except FileNotFoundError:
        flow = InstalledAppFlow.from_client_secrets_file(secrets_file, scopes)
        credentials = flow.run_console()
        save_crendentials(credentials)

    return googleapiclient.discovery.build(
        api_service_name, api_version, credentials=credentials)


def get_playlist_by_name(client, name):
    """Get a playlist by its name.
    """
    request = client.channels().list(
        part='contentDetails',
        mine=True)
    channel_info = request.execute()
    playlists = channel_info['items'][0]['contentDetails']['relatedPlaylists']
    return playlists[name]


def get_subs(client, **kwargs):
    """Get a user's subscripber information.
    """
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

    # Save subscribers to file before returning.
    save_subscriptions(subs)
    return subs


def get_channel_uploads(client, channel):
    """Get last 10 uploads from a channel.
    """
    # Only get the last 10 uploads.
    max_results = 10

    request = client.playlistItems().list(
        part='contentDetails',
        maxResults=max_results,
        playlistId=channel['playlists']['uploads'])
    uploads = request.execute()
    return uploads['items']


def add_video_to_playlist(client, video_id, playlist):
    """Add a video to a playlist.
    """
    request = client.playlistItems().insert(
        part='snippet',
        body={
            'snippet': {
                'playlistId': playlist,
                'resourceId': {
                    'kind': 'youtube#video',
                    'videoId': video_id}}})
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

    # Authenticate and get subs.
    client = authenticate(args.secrets_file)
    subs = get_subs(client, refresh_subs=args.refresh_subscriptions)

    if args.debug:
        print(json.dumps(subs))

    if args.verbose:
        print('Last run: {}'.format(last_run.strftime('%Y-%m-%d %H:%M:%S%Z')))
        print('Searching {} channels for new videos.'.format(len(subs)))
        print('==========================================================')

    # Search for new videos in subs.
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
            if published > last_run - timedelta(minutes=last_run_buffer):
                channel_videos.append(details)

        if args.verbose:
            print('  Found {} videos.'.format(len(channel_videos)))

        new_videos.extend(channel_videos)

    if args.debug:
        print(json.dumps(new_videos))

    # Add new videos to Watch later playlist.
    if len(new_videos):
        if args.verbose:
            print('==========================================================')
            print('Adding {} videos to Watch Later'.format(len(new_videos)))

        added = 0
        skipped = 0
        for video in new_videos:
            try:
                # ID for Watch later is always 'WL'.
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
    # Create configuration direcotory if it doesn't exist.
    if not os.path.exists(config_path):
        os.makedirs(config_path)

    signal(SIGINT, handler)
    sys.exit(main(sys.argv[1:]))

