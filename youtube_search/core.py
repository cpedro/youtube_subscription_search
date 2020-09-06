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
            self.build_client(creds)
            # Try and list 'my' channel, if this fails, will re-auth.
            request = self.client.channels().list(
                part="snippet,statistics",
                mine=True)
            request.execute()
        except Exception:
            creds = self.auth_client(secrets_file)
            self.build_client(creds)
            self.save_credentials(creds)

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

    def auth_client(self, secrets_file):
        """Authenticate against YouTube's API and return the credentials
        captured.
        """
        flow = InstalledAppFlow.from_client_secrets_file(
            secrets_file, self.settings.api_scopes)
        return flow.run_console()

    def build_client(self, creds):
        """Build the API client to use.  This requires credentials to use.
        """
        self._client = googleapiclient.discovery.build(
            self.settings.api_service_name, self.settings.api_version,
            credentials=creds)

    def load_credentials(self):
        """Load saved credentials from file.
        """
        with open(self.settings.credentials_file, 'rb') as fp:
            return pickle.load(fp)

    def save_credentials(self, credentials):
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

    def load_dest_playlist(self):
        """Load plalists from file.
        """
        try:
            with open(self.settings.dest_pl_file, 'rb') as fp:
                return pickle.load(fp)
        except FileNotFoundError:
            return None

    def save_dest_playlist(self, pl_id, pl_name):
        """Save playslists to file.
        """
        pl_info = {
            'last_update': datetime.now(timezone.utc),
            'name': pl_name,
            'id': pl_id}
        with open(self.settings.dest_pl_file, 'wb') as fp:
            pickle.dump(pl_info, fp, pickle.HIGHEST_PROTOCOL)

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

    def get_user_playlists(self):
        """Get list of user's playlists.
        """
        max_results = 50
        next_page = ''
        playlists = []

        while True:
            request = self.client.playlists().list(
                part='snippet,contentDetails',
                pageToken=next_page,
                maxResults=max_results,
                mine=True)
            playlists_list = request.execute()
            playlists.extend(p['snippet'] for p in playlists_list['items'])

            try:
                next_page = playlists_list('nextPageToken')
            except BaseException:
                break

        return playlists

    def get_user_subs(self):
        """Get a user's subscriber information.
        """
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

