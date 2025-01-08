# YouTube Video Uploader

A Python script for automating video uploads to YouTube with additional features like playlist assignment and geolocation data.

## Table of Contents
- [Description](#description)
- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Notes](#notes)
- [License](#license)

## Description
This script allows you to upload videos to YouTube with extra metadata such as playlist assignment and geographic coordinates.

## Requirements
- Python 3.x
- google-api-python-client
- oauth2client

## Installation
1. Install the required libraries:
   ```sh
   pip install google-api-python-client oauth2client
   ```
2. Obtain OAuth 2.0 credentials:
- Create a new project in the Google API Console: https://console.cloud.google.com/
- Go to "Library" and search for "YouTube Data API v3" to enable it.
- Create an OAuth 2.0 Client ID. Download the JSON file and save it as youtube_client_secrets.json.

## Configuration
Provide a config.cfg file with all necessary sections and keys (e.g., [Video], [Auth], [Settings]).

## Usage
Run the script from the command line. It will read the config file and upload the specified video to your YouTube channel.
   ```sh
   python3 youtube_upload.py 
   ```

# On the first run #
We have to authenticate to script for youtube uploads. Use the following command to do so:
 ```sh
   python3 youtube_upload.py --noauth_local_webserver
   ```

## Notes
Make sure you have valid OAuth credentials before running the script.
The uploaded video can be automatically assigned to a playlist if specified in the config file.