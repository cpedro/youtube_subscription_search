# -*- coding: utf-8 -*-
"""
File: youtube_search/core.py
Description: Core of YouTube Search API.  Defines the class and methods.
"""

__author__ = 'Chris Pedro'
__copyright__ = '(c) Chris Pedro 2020'
__licence__ = 'MIT'


import googleapiclient.discovery
import googleapiclient.errors
import os
import pickle

from .settings import Settings
from datetime import datetime, timedelta, timezone
from google_auth_oauthlib.flow import InstalledAppFlow


class YouTubeSearch(object):
    """YouTubeSearch class to perform various actions to search and update
    playlists.
    """

    def __init__(self, secrets_file='client_id.json'):
        """Authenticate to YouTube.  This will try and load saved credentials
        first and if it's not successful it will prompt the user for access and
        save credentials for the next run.
        """
        self._settings = Settings()
        # Create configuration directory if it doesn't exist.
        if not os.path.exists(self.settings.config_path):
            os.makedirs(self.settings.config_path)

        try:
            creds = self.load_credentials()
        except FileNotFoundError:
            flow = InstalledAppFlow.from_client_secrets_file(
                secrets_file, self.settings.api_scopes)
            creds = flow.run_console()
            self.save_crendentials(creds)

        self._client = googleapiclient.discovery.build(
            self.settings.api_service_name, self.settings.api_version,
            credentials=creds)

    @property
    def client(self):
        """YouTube client to use for all API calls.
        """
        return self._client

    @property
    def settings(self):
        """Settings to use.
        """
        return self._settings

    def load_credentials(self):
        """Load saved credentials from file.
        """
        with open(self.settings.credentials_file, 'rb') as fp:
            return pickle.load(fp)

    def save_crendentials(self, credentials):
        """Save credentials to file.
        """
        with open(self.settings.credentials_file, 'wb') as fp:
            pickle.dump(credentials, fp, pickle.HIGHEST_PROTOCOL)

    def load_last_run(self):
        """Load last run time from file.
        """
        try:
            with open(self.settings.last_run_file, 'rb') as fp:
                last_run = pickle.load(fp)
                # Backwards compatibility w/ <0.0.2 when last_run was datetime.
                if isinstance(last_run, datetime):
                    last_run = {'found_videos': [], 'last_run': last_run}
        except FileNotFoundError:
            # If there is no last run, tell program it was X days ago.
            last_run = {
                'found_videos': [],
                'last_run': datetime.now(timezone.utc) - timedelta(
                    days=self.settings.last_run_days_ago)}
        return last_run

    def save_last_run(self, found_videos):
        """Save 'last run', which is just the current time to file.
        """
        last_run = {
            'last_run': datetime.now(timezone.utc),
            'found_videos': found_videos}
        with open(self.settings.last_run_file, 'wb') as fp:
            pickle.dump(last_run, fp, pickle.HIGHEST_PROTOCOL)

    def load_subscriptions(self):
        """Load subscriptions from file.
        """
        with open(self.settings.subs_file, 'rb') as fp:
            return pickle.load(fp)

    def save_subscriptions(self, subs):
        """Save subscribers to file.
        """
        sub_info = {
            'last_update': datetime.now(timezone.utc),
            'subscriptions': subs}
        with open(self.settings.subs_file, 'wb') as fp:
            pickle.dump(sub_info, fp, pickle.HIGHEST_PROTOCOL)

    def get_playlist_by_name(self, name):
        """Get a playlist by its name.
        """
        request = self.client.channels().list(
            part='contentDetails',
            mine=True)
        channel_info = request.execute()
        content_details = channel_info['items'][0]['contentDetails']
        playlists = content_details['relatedPlaylists']
        return playlists[name]

    def get_subs(self, **kwargs):
        """Get a user's subscriber information.
        """
        if 'refresh_subs' not in kwargs or not kwargs['refresh_subs']:
            try:
                s_subs = self.load_subscriptions()
                # Backwards compatibility w/ <v0.2.0, will force sub reload.
                if type(s_subs) in [dict, set]:
                    if 'last_update' not in s_subs:
                        return s_subs['subscriptions']
                    elif (s_subs['last_update'] > datetime.now(timezone.utc)
                          - timedelta(days=self.settings.subs_days_old)):
                        return s_subs['subscriptions']
            except FileNotFoundError:
                pass

        max_results = 50
        next_page = ''
        subs = []

        # First get all subscriptions.
        while True:
            request = self.client.subscriptions().list(
                part='snippet,contentDetails',
                pageToken=next_page,
                maxResults=max_results,
                mine=True)
            sub_list = request.execute()

            subs.extend(sub['snippet'] for sub in sub_list['items'])

            try:
                next_page = sub_list['nextPageToken']
            except BaseException:
                break

        # Next loop through subs and get their public playlists.
        for sub in subs:
            request = self.client.channels().list(
                part='contentDetails',
                id=sub['resourceId']['channelId'])
            channel_info = request.execute()
            content_details = channel_info['items'][0]['contentDetails']
            sub['playlists'] = content_details['relatedPlaylists']

        # Save subscribers to file before returning.
        self.save_subscriptions(subs)
        return subs

    def get_channel_uploads(self, channel):
        """Get last 10 uploads from a channel.
        """
        # Only get the last 10 uploads.
        max_results = 10

        request = self.client.playlistItems().list(
            part='contentDetails',
            maxResults=max_results,
            playlistId=channel['playlists']['uploads'])
        uploads = request.execute()
        return uploads['items']

    def add_video_to_playlist(self, video_id, playlist):
        """Add a video to a playlist.
        """
        request = self.client.playlistItems().insert(
            part='snippet',
            body={
                'snippet': {
                    'playlistId': playlist,
                    'resourceId': {
                        'kind': 'youtube#video',
                        'videoId': video_id}}})
        return request.execute()

