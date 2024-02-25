import requests
import urllib.parse
import json
import os
import base64
import webbrowser
import random
from unidecode import unidecode
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

    def __init__(self, client_id, client_secret, access_token, refresh_token, credentials_file):
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.credentials_file = credentials_file
        self.user_id = self.get_user_id()


    def __str__(self):
        return f"A spotify app for user {self.user_id}" 


    def auth_header(self):
        return {"Authorization": f"Bearer {self.access_token}"}


    def get_user_id(self):
        # function doubles as a way to check the status of access token (expired or not)
        num_retries = 5
        for _ in range(num_retries):
            user_profile = requests.get('https://api.spotify.com/v1/me', headers=self.auth_header())
            if user_profile.status_code == 401:
                print("Access Token expired. Refreshing token")
                self._refesh_token()
                continue
            elif user_profile.status_code == 200:
                user_id = user_profile.json()["id"]
                return user_id
            
        raise SystemExit("Could not refresh token")
    

    def _refesh_token(self):
        auth_base64 = base64.b64encode(self.client_id.encode() + b':' + self.client_secret.encode()).decode("utf-8")

        url = "https://accounts.spotify.com/api/token"
        req_headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": "Basic " + auth_base64
        }
        req_data = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token
        }

        token_request = requests.post(url, headers=req_headers, data=req_data)

        if token_request.status_code == 200:
            self.access_token = token_request.json()["access_token"]
            SpotifyClient._save_credentials(self.access_token,  refresh_token=None, credentials_file=self.credentials_file)
            # TODO If refresh request fails, ask user to re-authenticate


    def create_playlist(self, name, descr, public=True, collab=False):
        endpoint = f"https://api.spotify.com/v1/users/{self.user_id}/playlists"

        header = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
        }
        body = {
                "name": name,
                "public": public,
                "collaborative": collab,
                "description": descr
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


    def search_track(self, market, song_details:dict, type_="track", limit=50, offset=0):
        remove_limiters = str.maketrans('','', ":/?#[]@!$&'()*+,;=")  # API does not seem to work when queries have this even if properly converted

        query_string = f"track:{song_details['title'].translate(remove_limiters).split('feat')[0]} year:{song_details['year']}"
        
        endpoint = "https://api.spotify.com/v1/search"
        params = {
                "q": query_string,
                "type": type_, 
                "market": market,
                "limit": limit,
                "offset": offset,
        }
        while True:
            try:
                song = requests.get(endpoint, params=params, headers=self.auth_header())

                if song.status_code == 200:
                    while True:
                        items = song.json()["tracks"]["items"]
                        if len(items) > 0:
                            # Check if artist matches
                            match_index = None
                            for index, item in enumerate(items):
                                result_artist_set = set()
                                artists = item["artists"]

                                for artist in artists:
                                    result_artist_set.add(unidecode(artist["name"].lower()))

                                input_artist_set = set(song_details['artist'].lower().split(', '))
                                artist_match = input_artist_set.intersection(result_artist_set)

                                if len(artist_match) > 0:
                                    match_index = index
                                    break

                            # Matching track is assumed correct
                            if match_index is not None:
                                print(f"{song_details['title']}: {items[match_index]['external_urls']['spotify']}")
                                return items[match_index]["id"]
                            else:
                                next_endpoint = song.json()["tracks"]["next"]
                                if next_endpoint is None:  # No more items to return
                                    print(f"{song_details['title']}: Did not find the track")
                                    return None
                                else:
                                    try:
                                        temp = requests.get(next_endpoint, headers=self.auth_header())
                                        if temp.status_code == 429:
                                            raise SpotifyRateException
                                    except SpotifyRateException:
                                        retry_time = int(temp.headers['retry-after'])
                                        print(f"Rate limit exceeded, sleeping for {retry_time} seconds")
                                        time.sleep(retry_time)
                                    else:
                                        song = temp
                                    finally:
                                        continue
                        else: 
                            print(f"{song_details['title']}: Did not find the track")
                            return None
                elif song.status_code == 429:
                    raise SpotifyRateException
                else:
                    print(json.dumps(song.json(), indent=4, sort_keys=True))
                    raise SystemExit("An error occured")
            except SpotifyRateException:
                    retry_time = int(song.headers['retry-after'])
                    print(f"Rate limit exceeded, sleeping for {retry_time} seconds")
                    time.sleep(retry_time)
                    
        

    def add_track(self, playlist_id, track_id_list):
        endpoint = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"

        header = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
        }
        body = {
                "uris": list(map(lambda track_id:"spotify:track:" + track_id, track_id_list)),
                "position": 0
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


    def get_track_features(self, track_id):
        endpoint = f"https://api.spotify.com/v1/audio-features/{track_id}"

        if track_id is None:
            return None
        
        while True:
            try:
                features_response = requests.get(endpoint, headers=self.auth_header())
                
                if features_response.status_code == 200:
                    features = features_response.json()
                    features_dict = {
                                "acousticness": features["acousticness"],
                                "danceability": features["danceability"],
                                "energy": features["energy"],
                                "instrumentalness": features["instrumentalness"],
                                "liveness": features["liveness"],
                                "loudness": features["loudness"],
                                "speechiness": features["speechiness"],
                                "tempo": features["tempo"],
                                "time_signature": features["time_signature"],
                                "valence": features["valence"]
                    } 
                    return features_dict
                
                elif features_response.status_code == 429:
                    raise SpotifyRateException
                elif features_response.status_code == 401:
                    print("Access Token expired")
                    # TODO Handle this later
                else:
                    print(json.dumps(features_response.json(), indent=4))
                    raise SystemExit("Error in getting track features")
            except SpotifyRateException:
                retry_time = int(features_response.headers['retry-after'])
                print(f"Rate limit exceeded, sleeping for {retry_time} seconds")
                time.sleep(retry_time)

    def get_recommendations(self, market, track_ids:list, limit=50):
        seed_track = random.sample(track_ids, 5)
        endpoint = "https://api.spotify.com/v1/recommendations"
        
        params = {
            "seed_tracks": ','.join(seed_track),
            "limit": limit,
            market: market
        }
        reco_request =requests.get(endpoint, params=params, headers=self.auth_header())

        if reco_request.status_code == 200:
            reco_track_ids = []
            reco_tracks = reco_request.json()["tracks"]
            for track in reco_tracks:
                reco_track_ids.append(track['id'])
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
    def get_credentials(cls, credentials_file):
        with open(credentials_file, 'r') as f:
            credentials = json.load(f)

        client_id = credentials["sptfy_id"]
        client_secret = credentials["sptfy_secret"]
        access_token = credentials["access_token"]
        refresh_token = credentials["refresh_token"]

        if access_token is None:
            auth_code = SpotifyClient._request_auth(client_id)
            access_token, refresh_token = SpotifyClient._request_new_token(client_id, client_secret, auth_code, credentials_file)

        return cls(client_id, client_secret, access_token, refresh_token, credentials_file)
    

    @staticmethod
    def _request_auth(client_id):
        auth_headers = {"client_id" : client_id,
                         "response_type": "code",
                         "redirect_uri": "http://localhost:7777/callback",
                         "scope": "playlist-modify-public playlist-modify-private"
                        }

        webbrowser.open("https://accounts.spotify.com/authorize?" + urllib.parse.urlencode(auth_headers))

        auth_code = input("Please enter callback code: ")
        
        return auth_code


    @staticmethod
    def _request_new_token(client_id, client_secret, auth_code, credentials_file):

        auth_base64 = base64.b64encode(client_id.encode() + b':' + client_secret.encode()).decode("utf-8")

        url = "https://accounts.spotify.com/api/token"
        req_headers = {
            "Authorization": "Basic " + auth_base64,
            "Content-Type": "application/x-www-form-urlencoded"
        }
        req_data = {
            "grant_type": "authorization_code",
            "code": auth_code,
            "redirect_uri" : "http://localhost:7777/callback"
        }

        token_request = requests.post(url, headers=req_headers, data=req_data)
        if token_request.status_code == 200:
            token_request_json = token_request.json()

            access_token = token_request_json["access_token"]
            refresh_token = token_request_json["refresh_token"]

            SpotifyClient._save_credentials(access_token,  refresh_token, credentials_file)
        else:
            raise SystemExit("Failed to get access token")
        
        return access_token, refresh_token


    @staticmethod
    def _save_credentials(access_token, refresh_token, credentials_file):
        with open(credentials_file, 'r') as f:
            credentials = json.load(f)

        credentials["access_token"] = access_token
        if refresh_token is not None:
            credentials["refresh_token"] = refresh_token

        with open(credentials_file, "w") as f:
            json.dump(credentials, f, indent=4)


if __name__ == "__main__":
    credentials = os.path.join(os.path.split(os.path.dirname(__file__))[0], 'credentials.json')
    app = SpotifyClient.get_credentials(credentials)

    # playlist_id = app.create_playlist("Summer Playlist by Philippe Petit", "Playlist created through Spotify API")

    test_song1 = {"title": "Remember",
                "artist": "Philippe Petit",
                "year": "2023"}    
    test_song2 = {"title": "Celeste",
                "artist": "Philippe Petit",
                "year": "2023"}
    test_song3 = {"title": "Perimeter",
                "artist": "JXTPS",
                "year": "2023"}
    test_song4 = {"title": "Exile",
                "artist": "Dimi Angelis",
                "year": "2023"}
    test_song5 = {"title": "Reset",
                "artist": "Decka",
                "year": "2023"}
    test_song6 = {"title": "Motor",
                "artist": "Roseen",
                "year": "2023"}
    test_song7 = {"title": "Imadub",
                "artist": "Kessell, Kerqus",
                "year": "2023"}
    test_song8 = {"title": "Igman",
                "artist": "Sev Dah",
                "year": "2023"}
    test_song9 = {"title": "Time to Expand",
                "artist": "Dying & Barakat",
                "year": "2023"}
    test_song10 = {"title": "Take It Off",
                "artist": "FISHER (OZ), Aatig",
                "year": "2023"}
    
    track_list = [test_song1, test_song2, test_song3, test_song4, test_song5, test_song6, test_song7, test_song8, test_song9, test_song10]
    track_id_list = []

    # for track in track_list:
    #     if track_id := app.search_track(market="PH", song_details=track):
    #         track_id_list.append(track_id)
    
    # app.add_track(playlist_id=playlist_id, track_id_list=track_id_list)
    # reco_track_ids = app.get_recommendations(market="PH", track_ids=track_id_list)
    # playlist_id2 = app.create_playlist("Recos Based on Summer By Philippe Petit ", "Playlist created through Spotify API")
    # app.add_track(playlist_id=playlist_id2, track_id_list=reco_track_ids)
    
    track_id = app.search_track(market="PH", song_details=test_song10)
