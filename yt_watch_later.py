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


import argparse
import dateutil.parser
import googleapiclient.discovery
import googleapiclient.errors
import json
import sys

from datetime import timedelta
from signal import signal, SIGINT
from youtube_search import YouTubeSearch


def parse_args(args):
    """Parse command line arguments.
    """
    parser = argparse.ArgumentParser(description='YouTube Subscription Search')
    parser.add_argument(
        '-s', '--secrets-file', default='client_id.json',
        help='Client secret file.  See README.md on how to get this file.')
    parser.add_argument(
        '-r', '--refresh-subscriptions', action='store_true',
        help='Force a refresh of subscriptions, and search subs.')
    parser.add_argument(
        '-R', '--just-refresh-subscriptions', action='store_true',
        help='Refresh subscriptions, and do not search subs.')
    parser.add_argument(
        '-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument(
        '-d', '--debug', action='store_true', help='Debug output')
    return parser.parse_args(args)


def get_user_subs(api, args):
    """Get the user's subscriptions.
    """
    refresh = args.refresh_subscriptions or args.just_refresh_subscriptions
    subs = api.get_user_subs(refresh_subs=refresh)
    if args.debug:
        print(json.dumps(subs))
    return subs


def get_new_videos(api, args, subs, last_runtime):
    """Get new viedoes uploaded since last run from subscriptions.
    """
    if args.verbose:
        msg = 'Last run: {}\n'
        'Searching {} channels for new videos.\n'
        '=========================================================='
        print((msg.format(
            last_runtime.strftime('%Y-%m-%d %H:%M:%S%Z'), len(subs))))

    new_videos = []
    for channel in subs:
        if args.verbose:
            print('Searching {}.'.format(channel['title']))
        uploads = api.get_channel_uploads(channel)
        channel_videos = []

        if args.debug:
            print(json.dumps(uploads))

        for video in uploads:
            details = video['contentDetails']
            published = dateutil.parser.isoparse(details['videoPublishedAt'])
            # Give a bit of a buffer to last run. This is needed because videos
            # sometimes take a while to appear in the API.
            if published > last_runtime - timedelta(
                    minutes=api.settings.last_run_buffer):
                channel_videos.append(details)

        if args.verbose:
            print('  Found {} videos.'.format(len(channel_videos)))

        new_videos.extend(channel_videos)

    if args.debug:
        print(json.dumps(new_videos))

    return new_videos


def add_new_videos_to_playlist(api, pl_name, pl_id, new_videos, last_videos):
    """Add all new videos to the selected playlist to be watched later.
    """
    if len(new_videos):
        print(('==========================================================\n'
               'Adding {} videos to {}'.format(len(new_videos), pl_name)))

        added = 0
        skipped = 0
        for video in new_videos:
            if video in last_videos:
                skipped += 1
                continue
            try:
                api.add_video_to_playlist(video['videoId'], pl_id)
                added += 1
            except googleapiclient.errors.HttpError:
                skipped += 1

        print(('==========================================================\n'
               '{} videos added.\n'
               '{} videos already added to playlist.').format(added, skipped))
    else:
        print(('==========================================================\n'
               'No videos to add.'))


def main(args):
    """Main method.
    """
    args = parse_args(args)
    api = YouTubeSearch(secrets_file=args.secrets_file)

    last_run = api.load_last_run()
    last_runtime = last_run['last_run']
    last_videos = last_run['found_videos']

    # TODO: Remove hardcode for Watch Later.
    pl_name = 'Watch Later'
    pl_id = 'WL'

    subs = get_user_subs(api, args)
    if args.just_refresh_subscriptions:
        return

    new_videos = get_new_videos(api, args, subs, last_runtime)
    add_new_videos_to_playlist(api, pl_name, pl_id, new_videos, last_videos)
    api.save_last_run(new_videos)


def handler(signal_received, frame):
    """Signal handler. Allows ^C to interrupt cleanly.
    """
    sys.exit(0)


if __name__ == '__main__':
    signal(SIGINT, handler)
    sys.exit(main(sys.argv[1:]))

