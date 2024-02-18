import spotify_client
import psycopg2
import psycopg2.extras
import os
import json
import argparse
import random

def chart_to_spotify(conn, spot_app):
    ...

def by_artist_to_spotify(conn, spot_app):
    ...

def by_genre_spotify(conn, spot_app):
    ...

def by_author_to_spotify(conn, spot_app):
    ...

# can query based on chart, artist, or genre
# limit results based on desired number, between release years, bpms, random or by number of appearances in charts

if __name__ == '__main__':
    credentials_path = os.path.join(os.path.dirname(__file__), 'credentials.json')

    with open(credentials_path, 'r') as f:
        credentials = json.load(f)

    conn = psycopg2.connect(dbname=credentials["database"], 
                            user=credentials["username"], 
                            host=credentials["hostname"], 
                            password=credentials["password"])

    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    query = "SELECT DISTINCT chart_name, chart_author FROM tracks LIMIT 10;"

    cur.execute(query)
    result = cur.fetchall()

    for row in result:
        print(row["chart_name"])

    # app = spotify_client.SpotifyClient.get_credentials(credentials_path)
    # print(app)

    # Close connection after running script
    cur.close()
    conn.close()



