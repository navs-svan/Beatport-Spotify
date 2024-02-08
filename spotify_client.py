import requests
from urllib.parse import urlencode 
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

    def __str__(self):
        return "My app" 
    
    def auth_header(self):
        return {"Authorization": f"Bearer {self.access_token}"}


    def test_token_status(self):
        test = requests.get('https://api.spotify.com/v1/me', headers=self.auth_header())

        if test.status_code in (400, 401):
            print("Access Token expired. Refreshing token")
            self._refesh_token()
    
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

    def search_song(self):
        pass

    def add_song_to_playlist(self):
        pass

    def _check_expiry(self):
        pass

    def main(self):
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
            access_token, refresh_token, basic_token = SpotifyClient._request_new_token(client_id, client_secret, auth_code, credentials_file)

        return cls(client_id, client_secret, access_token, refresh_token, credentials_file)
    
    @staticmethod
    def _request_auth(client_id):
        url = "https://accounts.spotify.com/authorize"

        auth_headers = {"client_id" : client_id,
                         "response_type": "code",
                         "redirect_uri": "http://localhost:7777/callback",
                         "scope": "playlist-modify-public playlist-modify-private"
                        }

        webbrowser.open("https://accounts.spotify.com/authorize?" + urlencode(auth_headers))

        # auth_code = input("Please enter callback code: ")
        auth_code = "AQAbMTp-l27R8E4Bz-1ZZHK87Z7eMD1-fGcN7KB41t2expr-Dtd5o75WHBuxi0f2gqkApVS-GIJr4B1Nll1rupnaxArHw2PJM6-o0JOP1QlMGcSyvP4ZOt85bsMCmLlE7pt-kYploEzHCvAvImyD0Ua4yqZcrzgks_xg43IeVqUSkhmE5WxPnTpsJXq_a8RPzD7jeW1uUxzRH--bzDK5lu2iZULCVTpxU1lesqH6b_QKclY"
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
    app.test_token_status()
