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
                    track_title AS title,
                    track_artist AS artist,
                    EXTRACT('Year' FROM track_date) AS "year"
                FROM tracks
                WHERE chart_name ILIKE %s
                AND chart_author ILIKE %s;
            """

    cur.execute(query, chart_details)
    tracks = cur.fetchall()
    
    # Spotify API
    playlist_id = spot_app.create_playlist(f"{tracks[0]['chart_name']} by {tracks[0]['chart_author']}", "Playlist created through Spotify API")
    
    track_id_list = []
    for track in tracks:
        if track_id := app.search_track(market="PH", song_details=track):
            track_id_list.append(track_id)

    app.add_track(playlist_id=playlist_id, track_id_list=track_id_list)


def by_artist_to_spotify(cur, spot_app, artist, limit=50, year_range=None):
    # SQL query
    if year_range:
        query = """
                    SELECT 
                        DISTINCT track_title as title, 
                        track_artist as artist,
                        EXTRACT('Year' FROM track_date) AS year
                    FROM tracks
                    WHERE track_artist ILIKE %s
                    AND track_date BETWEEN %s AND %s;
                """
        cur.execute(query, (artist, f"{year_range[0]}-01", f"{year_range[1]}-31"))
    else:
        query = """
                    SELECT 
                        DISTINCT track_title AS title, 
                        track_artist AS artist,
                        EXTRACT('Year' FROM track_date) AS year
                    FROM tracks
                    WHERE track_artist ILIKE %s;
                """
        cur.execute(query, (artist,))

    tracks = cur.fetchall()

    try:
        limited_tracks = random.sample(tracks, limit)
    except ValueError:
        limited_tracks = tracks
 
    # Spotify API
    playlist_id = spot_app.create_playlist(f"Tracks by {tracks[0]['artist']}", "Playlist created through Spotify API")
    
    track_id_list = []
    for track in limited_tracks:
        if track_id := app.search_track(market="PH", song_details=track):
            track_id_list.append(track_id)

    app.add_track(playlist_id=playlist_id, track_id_list=track_id_list)


def by_genre_spotify(cur, spot_app, genre, limit=50, mode="top", year_range=None):
    # SQL query
    if year_range:
        query = """
                    WITH ranking AS (
                    SELECT 
                        track_title,
                        track_genre,
                        track_artist,
                        COUNT(DISTINCT chart_name) AS chart_count
                    FROM tracks GROUP BY track_title, track_genre, track_artist
                    ORDER BY COUNT(DISTINCT chart_name) DESC 
                    )

                    SELECT 
                        DISTINCT t.track_title AS title, 
                        t.track_artist AS artist,
                        t.track_genre,
                        r.chart_count,
                        EXTRACT('Year' FROM track_date) AS year
                    FROM tracks t
                    JOIN ranking r
                        ON t.track_title = r.track_title
                        and t.track_artist = r.track_artist
                    WHERE t.track_genre ILIKE %s
                    AND t.track_date BETWEEN %s AND %s
                    ORDER BY r.chart_count DESC;
                """
        cur.execute(query, (genre, f"{year_range[0]}-01", f"{year_range[1]}-31"))
    else:
        query = """
                    WITH ranking AS (
                    SELECT 
                        track_title,
                        track_genre,
                        track_artist,
                        COUNT(DISTINCT chart_name) AS chart_count
                    FROM tracks GROUP BY track_title, track_genre, track_artist
                    ORDER BY COUNT(DISTINCT chart_name) DESC 
                    )

                    SELECT 
                        DISTINCT t.track_title AS title, 
                        t.track_artist AS artist,
                        t.track_genre,
                        r.chart_count,
                        EXTRACT('Year' FROM track_date) AS year
                    FROM tracks t
                    JOIN ranking r
                        ON t.track_title = r.track_title
                        and t.track_artist = r.track_artist
                    WHERE t.track_genre ILIKE %s
                    ORDER BY r.chart_count DESC;
                """
        cur.execute(query, (genre,))

    tracks = cur.fetchall()

    if mode == "top":
        limited_tracks = tracks[:limit]
    elif mode == "random":
        try:
            limited_tracks = random.sample(tracks, limit)
        except ValueError:
            limited_tracks = tracks

    # Spotify API
    playlist_id = spot_app.create_playlist(f"{tracks[0]['track_genre']} Genre Tracks ({mode})", "Playlist created through Spotify API")
    
    track_id_list = []
    for track in limited_tracks:
        if track_id := app.search_track(market="PH", song_details=track):
            track_id_list.append(track_id)

    app.add_track(playlist_id=playlist_id, track_id_list=track_id_list)


def by_author_to_spotify(cur, spot_app, chart_author:str):
    query = """
                SELECT 
                    chart_name, 
                    chart_author, 
                    chart_date
                FROM tracks
                GROUP BY 
                    chart_name, 
                    chart_author, 
                    chart_date
                HAVING chart_author ILIKE %s
                ORDER BY chart_date; 
            """
    
    cur.execute(query, (chart_author,))
    charts = cur.fetchall()
    for chart in charts:
        chart_details = (chart["chart_name"], chart_author)
        chart_to_spotify(cur=cur, spot_app=app, chart_details=chart_details)
    

def get_recommendation(cur, spot_app):
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


    # chart_details = ('Winter Grooves', 'Carlos Manaca')
    # chart_to_spotify(cur=cur, spot_app=app, chart_details=chart_details)

    # by_author_to_spotify(cur=cur, spot_app=app, chart_author="Todd Terry")

    # year_range = ('2023-06', '2024-01')
    # by_artist_to_spotify(cur=cur, spot_app=app, artist="Dompe", limit=50, year_range=year_range)

    # by_genre_spotify(cur, spot_app=app, genre="House", limit=30, mode="top", year_range=year_range)

    # Close connection after running script
    cur.close()
    conn.close()



