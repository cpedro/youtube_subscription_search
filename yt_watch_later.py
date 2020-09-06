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

from datetime import datetime, timedelta, timezone
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
        '-p', '--set-playlist', action='store_true',
        help='Set the playlist to save videos to.')
    parser.add_argument(
        '-P', '--just-set-playlist', action='store_true',
        help='Just set playlist to save videos to and exit.')
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


def ask_for_dest_playlist(api, args):
    """Prompt user for which playlist to save videos to.
    """
    playlists = api.get_user_playlists()
    if args.debug:
        print(json.dumps(playlists), file=sys.stderr)

    good_index = False
    while not good_index:
        try:
            print('0: Watch Later')
            for i, pl in enumerate(playlists):
                print('{}: {}'.format(i + 1, pl['title']))
            pl = int(input('Enter playlist index: '))
        except ValueError:
            continue
        good_index = (pl <= len(playlists) and pl >= 0)

    # Hack to allow 'Watch Later'
    if pl == 0:
        return 'WL', 'Watch Later'
    return playlists[pl - 1]['channelId'], playlists[pl - 1]['title']


def get_dest_playlist(api, args):
    """Gets the destination playlist to save to.
    """
    dest_playlist = api.load_dest_playlist()
    if args.set_playlist or args.just_set_playlist or not dest_playlist:
        pl_id, pl_name = ask_for_dest_playlist(api, args)
        api.save_dest_playlist(pl_id, pl_name)
        return pl_id, pl_name
    return dest_playlist['id'], dest_playlist['name']


def get_user_subs(api, args):
    """Get the user's subscriptions.
    """
    if not args.refresh_subscriptions and not args.just_refresh_subscriptions:
        try:
            s_subs = api.load_subscriptions()
            # Backwards compatibility w/ <v0.2.0, will force sub reload.
            if type(s_subs) in [dict, set]:
                if 'last_update' not in s_subs:
                    return s_subs['subscriptions']
                elif (s_subs['last_update'] > datetime.now(timezone.utc)
                      - timedelta(days=api.settings.subs_days_old)):
                    return s_subs['subscriptions']
        except FileNotFoundError:
            pass

    subs = api.get_user_subs()
    api.save_subscriptions(subs)

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
            print(json.dumps(uploads), file=sys.stderr)

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

    pl_id, pl_name = get_dest_playlist(api, args)
    if args.just_set_playlist:
        return

    subs = get_user_subs(api, args)
    if args.debug:
        print(json.dumps(subs), file=sys.stderr)
    if args.just_refresh_subscriptions:
        return

    new_videos = get_new_videos(api, args, subs, last_runtime)
    if args.debug:
        print(json.dumps(new_videos), file=sys.stderr)

    add_new_videos_to_playlist(api, pl_name, pl_id, new_videos, last_videos)

    api.save_last_run(new_videos)


def handler(signal_received, frame):
    """Signal handler. Allows ^C to interrupt cleanly.
    """
    sys.exit(0)


if __name__ == '__main__':
    signal(SIGINT, handler)
    sys.exit(main(sys.argv[1:]))

