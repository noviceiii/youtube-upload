# YouTube Video Uploader

This script is designed to upload videos to YouTube using the Google YouTube Data API v3. It handles authentication, video upload with retry logic for better reliability, and allows specifying video details like title, description, category, privacy status, location, and language.

*Absolutely no warranty given.*

## Create Google Youtube credentials
1.  Go to  [https://console.cloud.google.com/](https://console.cloud.google.com/)
2.  Create a new project.
3.  Choose from menu (or from the console start page): "APIs and services"
4.  Click
    -   "Library"
    -   Search for "YouTube Data API v3"
    -   Add/allow it.
5.  Click
    -   "Credentials"
    -   Then "+ Create Credentials"
    -   Choose:
        -   "OAuth client ID"
        -   Application type: "Desktop App"
        -   Give it a name
6.  Download the JSON of the newly created OAuth client.
7.  Save its content as youtube_client_secrets.json - or whatever matches your "client_secrets_file"-path in your config.cfg.

## Prerequisites

- **Python 3.x**
- **Google API Client Library for Python**
  - You can install it via pip:
    ```bash
    pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
    ```
- **Client Secrets File**
  - Download from Google Developer Console after setting up your YouTube Data API project. Set path in config.cfg to the downloaded file.
- **config.cfg** file with the following content:

    ```ini
    [authentication]
    client_secrets_file = /path/to/your/youtube_client_secrets.json
    oauth2_storage_file = /path/to/your/youtube_oauth2_store.json
    ```

## Usage

### Basic Usage

To upload a video with default settings:

```bash
python youtube-upload.py --videofile "/path/to/your/video.mp4"
```

For manual authentication in environments without local browsers (headless):

```bash
python youtube-upload.py --videofile "/path/to/video.mp4" --nolocalauth
```

## Parameters for the YouTube Upload Script
This script supports a variety of parameters to customize the upload process:

| Parameter               | Description                                                      | Example Values / Format                                                                 |
|-------------------------|------------------------------------------------------------------|----------------------------------------------------------------------------------------|
| `--videofile`           | Path to the video file that needs to be uploaded.                | `myvideo.mp4`                                                                          |
| `--title`               | Title of the video.                                              | `"My New Video"`                                                                       |
| `--description`         | Description of the video.                                        | `"A great video about..."`                                                             |
| `--category`            | Category ID for the video. See YouTube Categories.               | `22` (People & Blogs)                                                                  |
| `--keywords`            | Keywords for the video, separated by commas.                     | `"python, youtube, upload"`                                                            |
| `--privacyStatus`       | Privacy status of the video.                                     | `public`, `private`, `unlisted`                                                        |
| `--nolocalauth`         | Use authentication without local browser.                        | (Flag, no input required)                                                              |
| `--latitude`            | Latitude of the video's location.                                | `48.137154`                                                                            |
| `--longitude`           | Longitude of the video's location.                               | `11.576124`                                                                            |
| `--language`            | Language of the video.                                           | `en` (default), `de`                                                                   |
| `--playlistId`          | ID of the playlist to which the video should be added.           | `PL12345ABCDEF` for `youtube.com/playlist?list=PL12345ABCDEF`                          |
| `--thumbnail`           | Path to the thumbnail image file.                                | `path/to/thumbnail.jpg`                                                                |
| `--license`             | License of the video.                                            | `youtube`, `creativeCommon`                                                            |
| `--publishAt`           | ISO 8601 timestamp for scheduling video publish time.            | `2023-12-25T10:00:00Z`                                                                 |
| `--publicStatsViewable` | Whether video statistics should be public.                       | (Flag, no input required)                                                              |
| `--madeForKids`         | Whether the video is made for kids. Default: false.              | (Flag, no input required)                                                              |
| `--ageGroup`            | Target audience by age group.                                    | `age18_24`, `age25_34`                                                                 |
| `--gender`              | Target audience by gender.                                       | `male`, `female`                                                                       |
| `--geo`                 | Geographic targeting for the video (comma-separated country codes). | `US`, `CA`, `UK`                                                                       |
| `--defaultAudioLanguage`| Default audio language for the video.                            | `en-US`, `de-DE`                                                                       |

## Examples
1. Upload a video with custom title and description:

    ```bash
    python youtube-upload.py --videofile="/path/to/video.mp4" --title="My Awesome Video" --description="This is a great video!"
    ```

2. Upload with specific privacy status and keywords:

    ```bash
    python youtube-upload.py --videofile="/path/to/video.mp4" --privacyStatus="unlisted" --keywords="python, programming, tutorial"
    ```

3. Upload with location information:

    ```bash
    python youtube-upload.py --videofile="/path/to/video.mp4" --latitude=48.8566 --longitude=2.3522 --language="de"
    ```

4. Update with some more stuff:

    ```bash
    python youtube-upload.py --videofile="/path/to/video.mp4" --title="Epic Journey" --description="A journey through the mountains" --category="17" --keywords="mountains,adventure,hiking" --privacyStatus="public" --nolocalauth --latitude=48.8566 --longitude=2.3522 --language="de"
    ```

## Notes
- Ensure that your client_secrets_file and oauth2_storage_file paths in the config.cfg are correct.
- The script will check for the existence of the video file and required configuration files before attempting to upload.
- If authentication fails or credentials are invalid, you will be prompted to re-authenticate.

## Troubleshooting
- If you encounter errors related to file paths, double-check your paths in both the command line and config.cfg.
- For authentication issues, make sure your Google API project has the YouTube Data API enabled and your client secrets are correct.

Happy uploading!

## kudos
See https://developers.google.com/youtube/v3/guides/uploading_a_video for reference.
Thanks to Tokland for the inspiration https://github.com/tokland/youtube-upload.