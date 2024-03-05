# Beatport-Spotify

Beatport-Spotify is a Python script that scrapes the contents of [Beatport's](https://www.beatport.com/) [DJ Charts](https://www.beatport.com/charts/all?page=1&per_page=150) and stores them into a Postgres database. The script was written for personal use so the Postgres database is stored in the local machine of the user. The contents scraped from the DJ Charts are the following:
* Chart URL
* Chart name 
* Chart date
* Chart author
* Track details
    * Title
    * Artist
    * Label
    * Remixer (if there is one)
    * Genre
    * BPM
    * Key
    * Release year
    * Duration

After obtaining the tracks inside the charts, their Spotify audio features were then retrieved through the [Spotify Web API](https://developer.spotify.com/documentation/web-api). However, some tracks are not available in Spotify or in a specific market region, so the Postgres table for the audio features contained `null` values. This script requires the user to have their own Spotify Developer App to have access to Spotify's multiple API endpoints. The collection of data from Beatport and Spotify API was combined in [`pipeline.py`](pipeline.py)

This repository also includes a CLI Python script [`main.py`](main.py) to automate the creation of Spotify playlists using the collected data from Beatport's DJ Charts. There is also an option to create playlists using Spotify's `/recommendation` endpoint.   

The CLI script currently supports four ways of creating playlists. 
* Chart - creates a playlist based on a specified DJ Chart. Tracks inside this chart that are available in Spotify will be added to a playlist.
* Author - all charts made by a specified DJ will be converted into playlists. Each chart will have their own separate playlist.   
* Artist - tracks made by an artist will be collected into a single playlist. 
* Genre - tracks of a certain genre will be collected into a single playlist.



## Prerequisites

1. Python 3

2. Spotify Account
 
3. Postgres local installation


## Configuration
* Python
```
pip install -r requirements.txt
```
* Postgres
    * Create a Postgres database
    * Update the values of `hostname`, `username`, `password`, and `database` in the [credentials file](credential.json)
* Scrapeops (Optional)
    * Create a **free** [Scrapeops](https://scrapeops.io/app/dashboard) account
    * Retrieve [Fake Headers](https://scrapeops.io/app/headers) _API key_ 
    * Update the value of `scrapeops_api` in the [credentials file](credential.json)

    * If the user is not interested in using fake headers, disable the `beatportscraper.middlewares.ScrapeOpsFakeBrowserHeaders` downloader middleware in the scrapy [settings.py](./beatportscraper/settings.py)

* Spotify Developer App
    * Create an app on the [Spotify Developer](https://developer.spotify.com) site
        * Spotify's [tutorial](tutorial)
        * Add the `http://localhost:7777/callback` value to the _Redirect URIs_ within the app dashboard.
    * Retrieve the _Client ID_ and _Client secret_
    * Update the value of `sptfy_id` and `sptfy_secret` in the [credentials file](credential.json)


## Authentication
The [`spotify_client.py`](./src/spotify_client.py), which is responsible for communicating with various Spotify API endpoints, uses the Authorization Code Flow for user authentication. The user will grant permission scopes of `playlist-modify-public` and `playlist-modify-public` to allow the application to create Spotify playlists,  


### Initial Authentication
The first time the user runs the `pipeline.py` script, a web browser should open to the the Spotify authentication page. If the user grants the requested permission, they will be redirected to the url added to the _Redirect URIs_ earlier. 

The browser will display something like "This site can't be reached localhost refused to connect". This behavior is expected and the user **SHOULD NOT CLOSE** the browser tab. Instead, the user should copy the URL of the redirected site. An example is provided is below.

```
http://localhost:7777/callback?code=AQAbMTp-l27R8E4Bz-1ZZHK87Z7eMD1-fGcN7KB41t2expr-Dtd5o75WHBuxi0f2gqkApVS-GIJr4B1Nll1rupnaxArHw2PJM6-o0JOP1QlMGcSyvP4ZOt85bsMCmLlE7pt-kYploEzHCvAvImyD0Ua4yqZcrzgks_xg43IeVqUSkhmE5WxPnTpsJXq_a8RPzD7jeW1uUxzRH--bzDK5lu2iZULCVTpxU1lesqH6b_QKclY
```

The script will then ask the user to input the callback code. Simply copy the code seen in the url. In the case of the sample url, the callback code is:
```
AQAbMTp-l27R8E4Bz-1ZZHK87Z7eMD1-fGcN7KB41t2expr-Dtd5o75WHBuxi0f2gqkApVS-GIJr4B1Nll1rupnaxArHw2PJM6-o0JOP1QlMGcSyvP4ZOt85bsMCmLlE7pt-kYploEzHCvAvImyD0Ua4yqZcrzgks_xg43IeVqUSkhmE5WxPnTpsJXq_a8RPzD7jeW1uUxzRH--bzDK5lu2iZULCVTpxU1lesqH6b_QKclY
```

The script will then automatically handle everything else beyond this point. The user's _Access Token_ and _Refresh Token_ will be automatically saved to the the [credentials file](credential.json). The _Access Token_ is used to access the API endpoints but only has a validity of one hour before it expires. The _Refresh Token_ is used to refresh this access token. The script automatically does this for the user. 

## Running

* Data Pipeline
    * The `pipeline.py` can be ran through the command line 
    * It can also be scheduled using the Windows Task Manager. Approximately 10-15 new charts are added daily.   

* CLI Script
    * Run the following command for more details of its usage and arguments
        * ```python main.py -h```
