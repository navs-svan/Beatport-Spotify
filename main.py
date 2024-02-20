import spotify_client
import psycopg2
import psycopg2.extras
import os
import json
import argparse
import random

def chart_to_spotify(cur, chart_details:tuple):
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
    
    title = f"{tracks[0]['chart_name']} by {tracks[0]['chart_author']}"
    return (tracks, title)


def by_artist_to_spotify(cur, artist, limit=50, year_range=None):
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
    
    title = f"Tracks by {tracks[0]['artist']}"

    return (limited_tracks, title)


def by_genre_spotify(cur, genre, limit=50, mode="top", year_range=None):
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

    title = f"{tracks[0]['track_genre']} Genre Tracks ({mode})"

    return (limited_tracks, title)
    

def by_author_to_spotify(cur, chart_author:str):
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
        yield (chart["chart_name"], chart_author)

    

# limit results based on desired number, between release years, bpms, random or by number of appearances in charts

if __name__ == '__main__':
    credentials_path = os.path.join(os.path.dirname(__file__), 'credentials.json')

    # Postgres Connection
    with open(credentials_path, 'r') as f:
        credentials = json.load(f)

    conn = psycopg2.connect(dbname=credentials["database"], 
                            user=credentials["username"], 
                            host=credentials["hostname"], 
                            password=credentials["password"])
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Main Body
    track_title_list = []

    # SPECIFIC CHART
    chart_details = ('Winter Grooves', 'Carlos Manaca')
    track_title_list = [chart_to_spotify(cur=cur, chart_details=chart_details)]

    # CHART AUTHOR
    # chart_details = by_author_to_spotify(cur=cur, chart_author="Tacoman")
    # for chart_detail in chart_details:
    #     tracks, title = chart_to_spotify(cur=cur, chart_details=chart_detail)
    #     track_title_list.append((tracks, title))

    # TRACK ARTIST
    # year_range = ('2023-06', '2024-01')
    # track_title_list = [by_artist_to_spotify(cur=cur, artist="Dompe", limit=50, year_range=year_range)]

    # TRACK GENRE
    # year_range = ('2023-06', '2024-01')
    # track_title_list = [by_genre_spotify(cur, genre="Hard Techno", limit=30, mode="top", year_range=year_range)]

    # RECOMMENDATION
    recommendation = False

    # Spotify API
    app = spotify_client.SpotifyClient.get_credentials(credentials_path)
    
    for track_title in track_title_list:
        track_id_list = []
        tracks, title = track_title[0], track_title[1]

        for track in tracks:
            if track_id := app.search_track(market="PH", song_details=track):
                track_id_list.append(track_id)

        if recommendation is True:
            reco_track_ids = app.get_recommendations(market="PH", track_ids=track_id_list, limit=30)
            title = title + '(recommendations)'
            playlist_id = app.create_playlist(title, "Playlist created through Spotify API")
            app.add_track(playlist_id=playlist_id, track_id_list=reco_track_ids)
        else:
            playlist_id = app.create_playlist(title, "Playlist created through Spotify API")
            app.add_track(playlist_id=playlist_id, track_id_list=track_id_list)


    # Close connection after running script
    cur.close()
    conn.close()



