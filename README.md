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
There are two config files with all necessary sections and keys (e.g., [Video], [Auth], [Settings]).
- config_auth_settings.cfg for script settings.
- config_video.cfg for video and youtube related settings.

There are examples included. Just rename them and adjust the settings according your needs.

## Usage
Run the script from the command line. It will read the config file and upload the specified video to your YouTube channel.
   ```sh
   python3 youtube_upload.py 
   ```

## the first run on a headless installation
We have to authenticate to script for youtube uploads. Use the following command if you have a headless installation.
 ```sh
   python3 youtube_upload.py --noauth_local_webserver
   ```