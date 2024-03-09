import requests
import urllib.parse
import json
import os
import datetime
import base64
import webbrowser
import random
from unidecode import unidecode
from collections.abc import Generator
import time


class SpotifyTokenException(Exception):
    def __init__(self, message=None, error_code=None):
        super().__init__(message)
        self.error = error_code


class SpotifyRateException(Exception):
    def __init__(self, message=None, error_code=None):
        super().__init__(message)
        self.error = error_code


class SpotifyClient:
    """
    A class used to connect to multiple Spotify API endpoints

    Attributes:
        client_id (str): Spotify Developer App client ID.
         client_secret (str): Spotify Developer App client secret.
         access_token (str): Spotify API access token.
         refresh_token (str): Spotify API refresh token.
         credentials_file (str): string literal of credentials file source path.
         user_id (str): Spotify user ID

    Methods:
        create_playlist(name, descr, public, collab):
            Creates a Spotify playlist
        search_track(market, song_details, type_, limit, offset):
            Searches a track and returns its Spotify ID
        add_track(playlist_id, track_id_list):
            Adds tracks to a Spotify playlist
        get_track_features(track_id_list):
            Retrieves Spotify audio features
        get_recommendations(market, track_id_list, limit):
            Retrieves track recommendations
        get_credentials
            A class function for setting up the class attributes
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        access_token: str,
        refresh_token: str,
        credentials_file: str,
    ) -> None:
        """
        Summary: Inits SpotifyClient class

        Args:
            client_id (str): Spotify Developer App client ID.
            client_secret (str): Spotify Developer App client secret.
            access_token (str): Spotify API access token.
            refresh_token (str): Spotify API refresh token.
            credentials_file (str): string literal of credentials file source path.
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.credentials_file = credentials_file
        self.user_id = self._get_user_id()

    def __str__(self):
        return f"A spotify app for user {self.user_id}"

    def _auth_header(self) -> dict:
        """
        Summary: Appends self.access_token token to a valid string format

        Returns:
            dict: Authorization parameter of request headers
        """
        return {"Authorization": f"Bearer {self.access_token}"}

    def _get_user_id(self) -> str:
        """
        Summary: Sends a GET request to API "Get Current User's Profile" endpoint

        Returns:
            str: Spotify user ID of the user

        Raises:
            SystemExit: An error occured when refreshing the token
        """
        num_retries = 5
        for _ in range(num_retries):
            user_profile = requests.get(
                "https://api.spotify.com/v1/me", headers=self._auth_header()
            )
            if user_profile.status_code == 401:
                print("Access Token expired. Refreshing token")
                self._refesh_token()
                continue
            elif user_profile.status_code == 200:
                user_id = user_profile.json()["id"]
                return user_id

        raise SystemExit("Could not refresh token")

    def _refesh_token(self) -> None:
        """
        Summary: Refreshes access token by sending a POST request to "Spotify Token" endpoint then updates the credentials.json file
        """
        auth_base64 = base64.b64encode(
            self.client_id.encode() + b":" + self.client_secret.encode()
        ).decode("utf-8")

        url = "https://accounts.spotify.com/api/token"
        req_headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": "Basic " + auth_base64,
        }
        req_data = {"grant_type": "refresh_token", "refresh_token": self.refresh_token}

        token_request = requests.post(url, headers=req_headers, data=req_data)

        if token_request.status_code == 200:
            self.access_token = token_request.json()["access_token"]
            SpotifyClient._save_credentials(
                self.access_token,
                refresh_token=None,
                credentials_file=self.credentials_file,
            )
            # TODO If refresh request fails, ask user to re-authenticate

    def create_playlist(
        self,
        name: str,
        descr: str = "Playlist created through Spotify API",
        public: bool = True,
        collab: bool = False,
    ) -> str:
        """
        Summary: Creates a Spotify playlist by sending a POST request to "Create Playlist" endpoint

        Args:
            name (str): Name of the playlist.
            descr (str): Description of the playlist.
            public (bool): = "public" setting of the playlist. Visibility of playlist will be set to public if
                the value provided is True.
            collab (bool): = "collaborative" setting of the playlist. The playlist will be collaborative if
                the value provided is False

        Returns:
            str: string literal of the spotify playlist id

        Raises:
            SystemExit: A response error aside from Rate Limit and Token Exceptions occurred
        """
        endpoint = f"https://api.spotify.com/v1/users/{self.user_id}/playlists"

        header = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        body = {
            "name": name,
            "public": public,
            "collaborative": collab,
            "description": descr,
        }

        playlist = requests.post(endpoint, headers=header, json=body)

        if playlist.status_code == 201:
            print("Created playlist")
            return playlist.json()["id"]
        elif playlist.status_code == 429:
            print("Rate limit exceeded")
            print(json.dumps(playlist.json(), indent=4, sort_keys=True))
            # TODO Handle this later
        else:
            print(json.dumps(playlist.json(), indent=4, sort_keys=True))
            raise SystemExit("Error in creating playlist")

    def search_track(
        self,
        market: str,
        song_details: dict,
        type_: str = "track",
        limit: int = 50,
        offset: int = 0,
    ) -> str | None:
        """
        Summary: Searches a track by sending a GET request to "Search for Item" endpoint. It uses the track title
            and year to search for potential tracks. The json response contains a list of potential tracks
            and each potential is then verified using the track artists.

        Args:
            market (str): country code of the market where the track is available
            song_details (dict): a dictionary containing the values of "title", "year", and "artist".
                {title: str, artist: str, year: datetime}
            type_ (str): type of content that will be searched. Default value of "tracks".
            limit (int): maximum number of results returned by the request. Values should range from 0-50.
            offset (int): the starting index of the json response list. Values should range from 0-1000.

        Returns:
            str: The Spotify track ID if a track is successfully found
            None: returns None if no tracks were found

        Raises:
            SpotifyRateException: Rate Limit is reached the function is running
            SpotifyTokenException: Access Token expires while the function is running
            SystemExit: A response error aside from Rate Limit and Token Exceptions occurred
        """
        remove_limiters = str.maketrans(
            "", "", ":/?#[]@!$&'()*+,;="
        )  # API does not seem to work when queries have this even if properly converted

        query_string = f"track:{song_details['title'].translate(remove_limiters).split('feat')[0]} year:{song_details['year'].year}"

        endpoint = "https://api.spotify.com/v1/search"
        params = {
            "q": query_string,
            "type": type_,
            "market": market,
            "limit": limit,
            "offset": offset,
        }
        connect_timeout = 10
        read_timeout = 10
        MAX_RETRIES = 10
        retry_count = 0
        while retry_count < MAX_RETRIES:
            try:
                song = requests.get(
                    endpoint,
                    params=params,
                    headers=self._auth_header(),
                    timeout=(connect_timeout, read_timeout),
                )

                if song.status_code == 200:
                    while True:
                        try:
                            items = song.json()["tracks"]["items"]
                        except KeyError:
                            return None  # The API sometimes returns a response even though it doesn't have tracks
                        if len(items) > 0:
                            # Check if artist matches
                            match_index = None
                            for index, item in enumerate(items):
                                result_artist_set = set()

                                try:
                                    artists = item["artists"]
                                except TypeError:
                                    # The Spotify web API does return arrays with null objects in them.
                                    # Often the reason is because the content is not available in the specified market.
                                    return None

                                for artist in artists:
                                    result_artist_set.add(
                                        unidecode(artist["name"].lower())
                                    )

                                input_artist_set = set(
                                    song_details["artist"].lower().split(", ")
                                )
                                artist_match = input_artist_set.intersection(
                                    result_artist_set
                                )

                                if len(artist_match) > 0:
                                    match_index = index
                                    break

                            # Matching track is assumed correct
                            if match_index is not None:
                                print(
                                    f"{song_details['title']}: {items[match_index]['external_urls']['spotify']}"
                                )
                                return items[match_index]["id"]
                            else:
                                next_endpoint = song.json()["tracks"]["next"]
                                if next_endpoint is None:  # No more items to return
                                    print(
                                        f"{song_details['title']}: Did not find the track"
                                    )
                                    return None
                                else:
                                    try:
                                        temp = requests.get(
                                            next_endpoint, headers=self._auth_header()
                                        )
                                        if temp.status_code == 429:
                                            raise SpotifyRateException
                                        elif temp.status_code == 401:
                                            raise SpotifyTokenException
                                    except SpotifyRateException:
                                        retry_time = (
                                            int(temp.headers.get("retry-after", 1)) * 2
                                        )  # we really don't want to get banned
                                        print(
                                            f"Rate limit exceeded, sleeping for {retry_time} seconds"
                                        )
                                        time.sleep(retry_time)
                                    except SpotifyTokenException:
                                        print("Access Token expired. Refreshing token")
                                        self._refesh_token()
                                        continue
                                    else:
                                        song = temp
                                    finally:
                                        continue
                        else:
                            print(f"{song_details['title']}: Did not find the track")
                            return None
                elif song.status_code == 429:
                    raise SpotifyRateException
                elif song.status_code == 401:
                    raise SpotifyTokenException
                elif song.status_code == 500:
                    print(json.dumps(song.json(), indent=4, sort_keys=True))
                    time.sleep(3)
                    continue
                else:
                    print(json.dumps(song.json(), indent=4, sort_keys=True))
                    raise SystemExit("An error occurred")
            except (
                requests.exceptions.ConnectTimeout,
                requests.exceptions.ReadTimeout,
                requests.exceptions.ConnectionError,
            ) as e:
                print(f"Error encountered: {e}")
                retry_count += 1
                print(f"Retrying... (Attempt {retry_count} of {MAX_RETRIES})")
                time.sleep(5)
                continue
            except SpotifyRateException:
                retry_time = (
                    int(song.headers.get("retry-after", 1)) * 2
                )  # we really don't want to get banned
                print(f"Rate limit exceeded, sleeping for {retry_time} seconds")
                time.sleep(retry_time)
            except SpotifyTokenException:
                print("Access Token expired. Refreshing token")
                self._refesh_token()
                continue

    def add_track(self, playlist_id: str, track_id_list: list) -> None:
        """
        Summary: Adds tracks to a Spotfiy playlist by sending a POST request to "Add Items to Playlist" endpoint

        Args:
            playlist_id (str): string literal of the Spotify playlist ID where tracks will be added
            track_id_list (list): a list containing Spotify track IDs

        Raises:
            SystemExit: A response error aside from Rate Limit and Token Exceptions occurred
        """
        endpoint = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"

        header = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        body = {
            "uris": list(
                map(lambda track_id: "spotify:track:" + track_id, track_id_list)
            ),
            "position": 0,
        }
        add_request = requests.post(endpoint, headers=header, json=body)
        if add_request.status_code == 201:
            print("Added tracks to playlist")
        elif add_request.status_code == 429:
            print("Rate limit exceeded")
            print(json.dumps(add_request.json(), indent=4, sort_keys=True))
            # TODO Handle this later
        else:
            print(json.dumps(add_request.json(), indent=4, sort_keys=True))
            raise SystemExit("Error in adding tracks")

    def get_track_features(
        self, track_id_list: list
    ) -> Generator[dict, None, None] | Generator[None, None, None]:
        """
        Summary: Retrieves the Spotify audio features by sending a GET request to "Get Track's Audio Features" endpoint.
            Caution should be used when using this function as the endpoint is easily rate limited.

        Args:
            track_id_list (str): A list containing string literals of Spotify track IDs. The maximum number of IDs in the
                list is strictly 100.

        Yields:
            dict: dictionary of  the audio features of each track.
            None: If the track does not have audio features.

        Raises:
            SpotifyRateException: Rate Limit is reached the function is running
            SpotifyTokenException: Access Token expires while the function is running
            SystemExit: A response error aside from Rate Limit and Token Exceptions occurred
        """
        endpoint = f"https://api.spotify.com/v1/audio-features"

        if track_id_list is None:
            return None

        params = {"ids": ",".join(track_id_list)}
        MAX_RETRIES = 10
        retry_count = 0
        while retry_count < MAX_RETRIES:
            try:
                features_response = requests.get(
                    endpoint, params=params, headers=self._auth_header()
                )

                if features_response.status_code == 200:
                    features = features_response.json()
                    for feature in features["audio_features"]:
                        if feature is not None:
                            features_dict = {
                                "acousticness": feature["acousticness"],
                                "danceability": feature["danceability"],
                                "energy": feature["energy"],
                                "instrumentalness": feature["instrumentalness"],
                                "liveness": feature["liveness"],
                                "loudness": feature["loudness"],
                                "speechiness": feature["speechiness"],
                                "tempo": feature["tempo"],
                                "time_signature": feature["time_signature"],
                                "valence": feature["valence"],
                            }
                            yield features_dict
                        else:
                            yield {}
                    break
                elif features_response.status_code == 429:
                    print(features_response.json())
                    raise SpotifyRateException
                elif features_response.status_code == 401:
                    raise SpotifyTokenException
                else:
                    print(json.dumps(features_response.json(), indent=4))
                    raise SystemExit("Error in getting track features")
            except SpotifyRateException:
                retry_time = (
                    int(features_response.headers.get("retry-after", 1)) * 2
                )  # we really don't want to get banned
                print(f"Rate limit exceeded, sleeping for {retry_time} seconds")
                time.sleep(retry_time)
            except SpotifyTokenException:
                print("Access Token expired. Refreshing token")
                self._refesh_token()
                continue
            except (
                requests.exceptions.ConnectTimeout,
                requests.exceptions.ReadTimeout,
                requests.exceptions.ConnectionError,
            ) as e:
                print(f"Error encountered: {e}")
                retry_count += 1
                print(f"Retrying... (Attempt {retry_count} of {MAX_RETRIES})")
                time.sleep(5)
                continue

    def get_recommendations(
        self, market: str, track_id_list: list, limit: int = 50
    ) -> list:
        """
        Summary: Generates track recommendation by sending a GET request to "Get Recommendations" endpoint.
            This function only uses track seeds to generate recommendations.

        Args:
            market (str): country code of the market where the tracks are available.
            track_id_list (list): list of Spotify track IDs to be used as seeds. A maximum of 5 IDs may be included.
            limit (int): target size of the list of recommended tracks. Values should range from 1-100.

        Returns:
            list: A list containing the Spotify track IDs of the recommended tracks

        Raises:
            SystemExit: A response error aside from Rate Limit and Token Exceptions occurred
        """
        seed_track = random.sample(track_id_list, 5)
        endpoint = "https://api.spotify.com/v1/recommendations"

        params = {"seed_tracks": ",".join(seed_track), "limit": limit, market: market}
        reco_request = requests.get(
            endpoint, params=params, headers=self._auth_header()
        )

        if reco_request.status_code == 200:
            reco_track_ids = []
            reco_tracks = reco_request.json()["tracks"]
            for track in reco_tracks:
                reco_track_ids.append(track["id"])
            print(f"Recommending {len(reco_track_ids)} tracks")
            return reco_track_ids
        elif reco_request.status_code == 429:
            print("Rate limit exceeded")
            print(json.dumps(reco_request.json(), indent=4, sort_keys=True))
            # TODO Handle this later
        else:
            print(json.dumps(reco_request.json(), indent=4, sort_keys=True))
            raise SystemExit("An error occured")

    @classmethod
    def get_credentials(cls, credentials_file: str) -> "SpotifyClient":
        """
        Summary: Retrieves the Spotify API credentials from the credentials.json file
            and sets up the class attributes.

        Args:
            credentials_file (str): string literal of credentials file source path.

        Returns:
            SpotifyClient: returns an instance of the class
        """
        with open(credentials_file, "r") as f:
            credentials = json.load(f)

        client_id = credentials["sptfy_id"]
        client_secret = credentials["sptfy_secret"]
        access_token = credentials["access_token"]
        refresh_token = credentials["refresh_token"]

        if access_token is None:
            auth_code = SpotifyClient._request_auth(client_id)
            access_token, refresh_token = SpotifyClient._request_new_token(
                client_id, client_secret, auth_code, credentials_file
            )

        return cls(
            client_id, client_secret, access_token, refresh_token, credentials_file
        )

    @staticmethod
    def _request_auth(client_id: str) -> str:
        """
        Summary: Authenticates the user through the Authorization Code Flow. The user will be redirected to a website where the "code"
            parameter should be retrieved from the callback. The "code" parameter should then inputted when asked by the program.

        Args:
            client_id (str): The Spotify Developer App Client ID

        Returns:
            str: returns the auth_code if the user accepts the authentication
        """
        _auth_headers = {
            "client_id": client_id,
            "response_type": "code",
            "redirect_uri": "http://localhost:7777/callback",
            "scope": "playlist-modify-public playlist-modify-private",
        }

        webbrowser.open(
            "https://accounts.spotify.com/authorize?"
            + urllib.parse.urlencode(_auth_headers)
        )

        auth_code = input("Please enter callback code: ")

        return auth_code

    @staticmethod
    def _request_new_token(
        client_id: str, client_secret: str, auth_code: str, credentials_file: str
    ) -> tuple:
        """
        Summary: Requests for an Access Token by sending a POST request to "Token" endpoint. Function then stores
            the Access Token and Refresh Token to the credentials.json file

        Args:
            client_id (str): Spotify Developer App client ID.
            client_secret (str): Spotify Developer App client secret.
            auth_code (str): Temporary authetication code.
            credentials_file (str): string literal of credentials file source path.

        Returns:
            tuple: The tuple (access_token, refresh_token) is returned

        Raises:
            SystemExit: A response error other than 200 occurred
        """

        auth_base64 = base64.b64encode(
            client_id.encode() + b":" + client_secret.encode()
        ).decode("utf-8")

        url = "https://accounts.spotify.com/api/token"
        req_headers = {
            "Authorization": "Basic " + auth_base64,
            "Content-Type": "application/x-www-form-urlencoded",
        }
        req_data = {
            "grant_type": "authorization_code",
            "code": auth_code,
            "redirect_uri": "http://localhost:7777/callback",
        }

        token_request = requests.post(url, headers=req_headers, data=req_data)
        if token_request.status_code == 200:
            token_request_json = token_request.json()

            access_token = token_request_json["access_token"]
            refresh_token = token_request_json["refresh_token"]

            SpotifyClient._save_credentials(
                access_token, refresh_token, credentials_file
            )
        else:
            raise SystemExit("Failed to get access token")

        return access_token, refresh_token

    @staticmethod
    def _save_credentials(
        access_token: str, refresh_token: str, credentials_file: str
    ) -> None:
        """
        Summary: Saves the access_token and refresh_token to the credentials.json file

        Args:
            access_token (str): Spotify API access token.
            refresh_token (str): Spotify API refresh token.
            credentials_file (str): string literal of credentials file source path.
        """
        with open(credentials_file, "r") as f:
            credentials = json.load(f)

        credentials["access_token"] = access_token
        if refresh_token is not None:
            credentials["refresh_token"] = refresh_token

        with open(credentials_file, "w") as f:
            json.dump(credentials, f, indent=4)


if __name__ == "__main__":
    credentials = os.path.join(
        os.path.split(os.path.dirname(__file__))[0], "credentials.json"
    )
    app = SpotifyClient.get_credentials(credentials)

    print(type(app))
    test_song1 = {"title": "Remember", "artist": "Philippe Petit", "year": datetime.datetime(2023, 9, 1)}
    test_song2 = {"title": "Celeste", "artist": "Philippe Petit", "year": datetime.datetime(2023, 9, 1)}
    test_song3 = {"title": "Perimeter", "artist": "JXTPS", "year": datetime.datetime(2023, 9, 1)}
    test_song4 = {"title": "Exile", "artist": "Dimi Angelis", "year": datetime.datetime(2023, 9, 1)}
    test_song5 = {"title": "Reset", "artist": "Decka", "year": datetime.datetime(2023, 9, 1)}
    test_song6 = {"title": "Motor", "artist": "Roseen", "year": datetime.datetime(2023, 9, 1)}
    test_song7 = {"title": "Imadub", "artist": "Kessell, Kerqus", "year": datetime.datetime(2023, 9, 1)}
    test_song8 = {"title": "Igman", "artist": "Sev Dah", "year": datetime.datetime(2023, 9, 1)}
    test_song9 = {
        "title": "Time to Expand",
        "artist": "Dying & Barakat",
        "year": "2023",
    }
    test_song10 = {
        "title": "100 Miles",
        "artist": "Nico Morano, MeWhy",
        "year": datetime.datetime(2023, 9, 1),
    }

    track_list = [
        test_song1,
        test_song2,
        test_song3,
        test_song4,
        test_song5,
        test_song6,
        test_song7,
        test_song8,
        test_song9,
        test_song10,
    ]
    track_id_list = []

    # playlist_id = app.create_playlist("Summer Playlist by Philippe Petit", "Playlist created through Spotify API")
    # for track in track_list:
    # if track_id := app.search_track(market="PH", song_details=track):
    #         track_id_list.append(track_id)
    # app.add_track(playlist_id=playlist_id, track_id_list=track_id_list)

    # reco_track_ids = app.get_recommendations(market="PH", track_ids=track_id_list)
    # playlist_id2 = app.create_playlist("Recos Based on Summer By Philippe Petit ", "Playlist created through Spotify API")
    # app.add_track(playlist_id=playlist_id2, track_id_list=reco_track_ids)

    # track_ids = ['7ouMYWpwJ422jRcDASZB7P','4VqPOruhp5EdPBeR92t6lQ','2takcwOaAZWiXQijPHIx7B', '6uLMxmK9MHb6fiecxn2yrp']

    # for feature in app.get_track_features(track_ids):
    #     print(feature)

    track_id = app.search_track(market="PH", song_details=test_song10)
    for feature in app.get_track_features([track_id]):
        print(feature)
