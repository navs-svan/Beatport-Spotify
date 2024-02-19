import spotify_client
import psycopg2
import psycopg2.extras
import os
import json
import argparse
import random

def chart_to_spotify(cur, spot_app, chart_details:tuple):
    # SQL query
    query = """
                SELECT 
                    chart_name,
                    chart_author,
                    track_title,
                    track_artist,
                    EXTRACT('Year' FROM track_date) AS "release_year"
                FROM tracks
                WHERE chart_name LIKE %s
                AND chart_author LIKE %s;
            """

    cur.execute(query, chart_details)
    results = cur.fetchall()
    
    track_list = []

    for row in results:
        track_list.append({"title": row["track_title"],
                            "artist": row["track_artist"],
                            "year": row["release_year"]})

    # Spotify API
    playlist_id = spot_app.create_playlist(f"{row['chart_name']} by {row['chart_author']}", "Playlist created through Spotify API")
    
    track_id_list = []
    for track in track_list:
        if track_id := app.search_track(market="PH", song_details=track):
            track_id_list.append(track_id)

    app.add_track(playlist_id=playlist_id, track_id_list=track_id_list)


def by_artist_to_spotify(conn, spot_app):
    ...

def by_genre_spotify(conn, spot_app):
    ...

def by_author_to_spotify(conn, spot_app):
    ...

def get_recommendation(conn, spot_app):
    ...
    
# can query based on chart, artist, or genre
# limit results based on desired number, between release years, bpms, random or by number of appearances in charts

if __name__ == '__main__':
    credentials_path = os.path.join(os.path.dirname(__file__), 'credentials.json')

    app = spotify_client.SpotifyClient.get_credentials(credentials_path)

    with open(credentials_path, 'r') as f:
        credentials = json.load(f)

    conn = psycopg2.connect(dbname=credentials["database"], 
                            user=credentials["username"], 
                            host=credentials["hostname"], 
                            password=credentials["password"])
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)


    chart_details = ('Winter Grooves', 'Carlos Manaca')
    chart_to_spotify(cur=cur, spot_app=app, chart_details=chart_details)


    # Close connection after running script
    cur.close()
    conn.close()



