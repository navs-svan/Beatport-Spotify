import spotify_client
import psycopg2
import os


if __name__ == '__main__':
    credentials = os.path.join(os.path.dirname(__file__), 'credentials.json')
    app = spotify_client.SpotifyClient.get_credentials(credentials)
    print(app)

