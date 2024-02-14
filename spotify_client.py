import requests
import urllib.parse
import json
import os
import base64
import webbrowser

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
    

    def main(self):
        playlist_id = self.create_playlist("Test Playlist", "Playlist created through Spotify API")

        test_song1 = {"title": "Dead Man",
                    "artist": "Night Shift",
                    "year": "2023"}    
        test_song2 = {"title": "My Addiction",
                    "artist": "Alex Guesta",
                    "year": "2020"}
        test_song3 = {"title": "wakakakakakkaa",
                    "artist": "Anya Forger",
                    "year": "2053"}
        
        track_list = [test_song1, test_song2, test_song3]
        track_id_list = []

        for track in track_list:
            if track_id := self.search_track(market="PH", song_details=track):
                track_id_list.append(track_id)

        self.add_song(playlist_id=playlist_id, track_id_list=track_id_list)



    def auth_header(self):
        return {"Authorization": f"Bearer {self.access_token}"}


    def get_user_id(self):
        # function doubles as a way to check the status of access token (expired or not)
        num_retries = 5
        for _ in range(num_retries):
            user_profile = requests.get('https://api.spotify.com/v1/me', headers=self.auth_header())
            # print(json.dumps(user_profile.json(), indent=4, sort_keys=True))
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
        print(token_request.json())
        if token_request.status_code == 200:
            self.access_token = token_request.json()["access_token"]
            SpotifyClient._save_credentials(self.access_token,  refresh_token=None, credentials_file=self.credentials_file)
            # If refresh request fails, ask user to re-authenticate


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
            # TODO Handle this later
        else:
            print(json.dumps(playlist.json(), indent=4, sort_keys=True))
            raise SystemExit("Error in creating playlist")


    def search_track(self, market, song_details:dict, type_="track", limit=1, offset=0):
                
        query_string = f"artist:{song_details['artist']} track:{song_details['title']} year:{song_details['year']}"
        
        endpoint = "https://api.spotify.com/v1/search"
        params = {
                "q": query_string,
                "type": type_, 
                "market": market,
                "limit": limit,
                "offset": offset,
        }

        song = requests.get(endpoint, params=params, headers=self.auth_header())

        if song.status_code == 200:
            items = song.json()["tracks"]["items"]
            if len(items) > 0:
                # First result, if there is, is assumed to be the correct track
                print(items[0]["external_urls"])
                return items[0]["id"]
            else: 
                print("Did not find the track")
                return None
        elif song.status_code == 429:
            print("Rate limit exceeded")
            # TODO Handle this later
        else:
            print(json.dumps(song.json(), indent=4, sort_keys=True))
            raise SystemExit("An error occured")
        

    def add_song(self, playlist_id, track_id_list):
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
            # TODO Handle this later
        else:
            print(json.dumps(add_request.json(), indent=4, sort_keys=True))
            raise SystemExit("Error in creating playlist") 


    def get_track_details(self):
        # https://developer.spotify.com/documentation/web-api/reference/get-audio-features
        pass


    def get_recommendations(self):
        # https://developer.spotify.com/documentation/web-api/reference/get-recommendations
        pass

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
    credentials = os.path.join(os.path.dirname(__file__), 'credentials.json')
    app = SpotifyClient.get_credentials(credentials)
    app.main()  
