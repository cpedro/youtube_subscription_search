# YouTube Subscription Search

Searches all of your subscrptions for new videos, since the last time the
program was run, or since 3 days ago.  If any videos were found, it will add
them to your "Watch later" playlist.

## Requirements
To make sure you have all requirements:

```bash
$ pip3 install -r requirements.txt
```

## Create an API key

Before you can run this program, you have to setup a project and API key in the
[Google Developer's website](https://console.developers.google.com/project/_/apiui/apis/library).  This will be used to make all API calls to YouTube using your account information.

1. Go to [Google Developer's website](https://console.developers.google.com/project/_/apiui/apis/library).
  Login using the same account that your YouTube account is tied to.
1. Click 'Create', and name your project.  You can call it 'YouTube Search' or
  anything else you wish.
1. Click 'Library' in the side bar.  Seaerch for 'YouTube Data API v3', and
  Enable.  Click back to Dashboard.
1. Click 'OAuth consent screen' in the side bar.  Create a new consent screen,
  type 'External'.  For Application name, you can use 'YouTube Search', or
  anything else you wish.  Level all options as default, and click 'Save' at the
  bottom of the window.
1. Click 'Credentials' in the side bar.  Click '+ Create Credentials' at the top
  page and select 'Help me choose'.
1. For 'Which API are you using?', select 'YouTube Data API v3'.
1. For 'Where you will be calling the API from?', select 'Other UI'.
1. Select 'User data', and click 'What credentials do I need?'.
1. Give a name to your credentials on the next page, and click 'Create OAuth
  client ID'.
1. You should be given an option to download, credentials, do this now.  This
  will save a file to your computer, called `client_id.json`.  Click 'Done'
  after downloading the file.
1. Copy the `client_id.json` file into the same directory as the python program.
  *OR* you can use the `-s` option when running the program the first time with
  the path to `client_id.json`.

## Running the program

Once the `client_id.json` file has been downloaded and saved to the same
directory as the program, you're good to go.  Just run `./watch_later.py` or
`python3 watch_later.py`.

You don't *need* to move `client_id.json` to the same directory, you also use
then `-s` option when calling the program with a path to the file.  This file
is only needed on the first run, after that, auth tokens will be saved for
future runs.

The first time you run the program, you will be prompted to visit a URL and
authorize this application.  This is normal, and will only be required once.
Open the URL in your browser, and follow through the steps on the Google
website.  You may also get a warning that this app isn't verified.  This is also
OK since it is using the project you created under your Google profile. Once you
have allowed the application to access your data, you will be sent to a page
with a code.  Copy this code, and paste it into your console and press enter.

Once this is done once, an authorization token will be saved to you computer
and used again in subsequent calls of the program.

## Important Notes

* This program will collect information about your subscriptions the first time
  it runs and use this cached information each time.  This is done to limit the
  amount of API calls it makes to avoid hitting Google API quotas.  If you 
  update your subscriptions at any time, such as subbing or unsubbing to 
  channels, you will need to refresh the cached data by running:
  ```bash
  watch_later.py -r
  ```
* If you want to see a more verbose output, and see what the program is doing,
  you can specify the `-v` command line option:
  ```bash
  watch_later.py -v
  ```

### General Usage
```
usage: watch_later.py [-h] [-s SECRETS_FILE] [-r] [-v] [-d]

YouTube Subscription Search

optional arguments:
  -h, --help            show this help message and exit
  -s SECRETS_FILE, --secrets-file SECRETS_FILE
                        Client secret file. See README.md on how to get this
                        file.
  -r, --refresh-subscriptions
                        Force a refresh of subscriptions.
  -v, --verbose         Verbose output
  -d, --debug           Debug output
```



### Cached files

The program will save subscriptions, security tokens and last run information in
`${HOME}/.config/youtube_subscription_search` (or
`%userprofile%\.config\youtube_subscription_search` in Windows).  If you ever
decide to uninstall this program, you can safely delete this config / cache
directory as well to tie up the loose ends.

