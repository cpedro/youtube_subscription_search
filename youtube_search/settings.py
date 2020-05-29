# -*- coding: utf-8 -*-
"""
File: youtube_search/settings.py
Description: Holds static settings for the YouTube Search core.
"""

__author__ = 'Chris Pedro'
__copyright__ = '(c) Chris Pedro 2020'
__licence__ = 'MIT'


import os

from pathlib import Path


class Settings(object):
    def __init__(self):
        """Initialise all properties.
        """
        # YouTube API settings.
        self._api_service_name = 'youtube'
        self._api_version = 'v3'
        self._api_scopes = ['https://www.googleapis.com/auth/youtube']

        # Files used to save states between runs.
        self._config_path = os.path.join(
            str(Path.home()), '.config', 'youtube_subscription_search')
        self._credentials_file = os.path.join(self._config_path, 'credentials')
        self._last_run_file = os.path.join(self._config_path, 'last_run')
        self._subs_file = os.path.join(self._config_path, 'subscriptions')

        # If last_run doesn't exist, set this many days ago to default value.
        self._days_ago = 3
        # Buffer for last_run to compare to new videos, in minutes.
        self._last_run_buffer = 60


    @property
    def api_service_name(self):
        """The API Service name, 'youtube'
        """
        return self._api_service_name


    @property
    def api_version(self):
        """The API version, 'v3'
        """
        return self._api_version


    @property
    def api_scopes(self):
        """The API scope, ['https://www.googleapis.com/auth/youtube']
        """
        return self._api_scopes


    @property
    def config_path(self):
        """The configuration path, ${HOME}/.config/youtube_subscription_search
        """
        return self._config_path


    @property
    def credentials_file(self):
        """File containing saved credentials, <config_path>/credentials
        """
        return self._credentials_file


    @property
    def last_run_file(self):
        """File containing last run information, <config_path>/last_run
        """
        return self._last_run_file


    @property
    def subs_file(self):
        """File containing cached subscriptions, <config_path>/subscriptions
        """
        return self._subs_file


    @property
    def days_ago(self):
        """If last_run doesn't exist, set this many days ago to run off of
        default = 3
        """
        return self._days_ago


    @property
    def last_run_buffer(self):
        """Buffer for last_run to compare to new videos, in minutes.
        default = 60
        """
        return self._last_run_buffer

