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


def main(args):
    """Main method.
    """
    args = parse_args(args)
    api = YouTubeSearch(secrets_file=args.secrets_file)

    last_run = api.load_last_run()
    last_runtime = last_run['last_run']
    last_found_videos = last_run['found_videos']
    refresh = args.refresh_subscriptions or args.just_refresh_subscriptions

    # Get subscriptions.
    subs = api.get_subs(refresh_subs=refresh)

    if args.just_refresh_subscriptions:
        return

    if args.debug:
        print(json.dumps(subs))

    if args.verbose:
        print(('Last run: {}\n'
               'Searching {} channels for new videos.'.format(
                last_runtime.strftime('%Y-%m-%d %H:%M:%S%Z'), len(subs))))
        print('==========================================================')

    # Search for new videos in subs.
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
            # Give 1 hour as a bit of a buffer to last run.
            if published > last_runtime - timedelta(
                    minutes=api.settings.last_run_buffer):
                channel_videos.append(details)

        if args.verbose:
            print('  Found {} videos.'.format(len(channel_videos)))

        new_videos.extend(channel_videos)

    if args.debug:
        print(json.dumps(new_videos))

    # Add new videos to Watch later playlist.
    if len(new_videos):
        print(('==========================================================\n'
               'Adding {} videos to Watch Later'.format(len(new_videos))))

        added = 0
        skipped = 0
        for video in new_videos:
            if video in last_found_videos:
                skipped += 1
                continue
            try:
                # ID for Watch later is always 'WL'.
                api.add_video_to_playlist(video['videoId'], 'WL')
                added += 1
            except googleapiclient.errors.HttpError:
                skipped += 1

        print(('==========================================================\n'
               '{} videos added.\n'
               '{} videos already added to playlist.').format(added, skipped))
    else:
        print(('==========================================================\n'
               'No videos to add.'))

    api.save_last_run(new_videos)


def handler(signal_received, frame):
    """Signal handler. Allows ^C to interrupt cleanly.
    """
    sys.exit(0)


if __name__ == '__main__':
    signal(SIGINT, handler)
    sys.exit(main(sys.argv[1:]))

