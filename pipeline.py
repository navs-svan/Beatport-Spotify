import os
import json
import psycopg2
import psycopg2.extras
import concurrent.futures
import itertools
import time

import src.spotify_client as spotify_client
from beatportscraper.spiders.beatportspider import BeatportspiderSpider
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings


def beatport_pipeline():
    settings = get_project_settings()
    process = CrawlerProcess(settings)
    process.crawl(BeatportspiderSpider)
    process.start()


def spotify_pipeline(conn, cur, app):
    cur.execute(""" 
            CREATE TABLE IF NOT EXISTS features(
                id serial PRIMARY KEY,
                track_id INT NOT NULL,
                acousticness NUMERIC,
                danceability NUMERIC,
                energy NUMERIC,
                instrumentalness NUMERIC,
                liveness NUMERIC,
                loudness NUMERIC,
                speechiness NUMERIC,
                tempo NUMERIC,
                time_signature INT,
                valence NUMERIC,
                FOREIGN KEY (track_id)
                    REFERENCES tracks(id)
            );              
        """)
    get_query = """
                SELECT 
                    t.id,
                    t.track_title as title,
                    t.track_artist as artist,
                    EXTRACT('Year' FROM t.track_date) AS year 
                FROM tracks t 
                WHERE NOT EXISTS (
                    SELECT id 
                    FROM features f 
                    WHERE t.id = f.track_id)
                ORDER BY t.id
                LIMIT 10
                ;
        """
    
    cur.execute(get_query)
    tracks = cur.fetchall()
    ids = [track["id"] for track in tracks]
    iter_app = itertools.repeat(app)

    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = executor.map(search_retrieve, tracks, ids, iter_app)

        for result in results:
            insert_data(result, conn, cur)

    # for track in tracks:
    #     features = search_retrieve(track, app)
        # insert_data(conn, cur, features, track["id"])


def search_retrieve(track_details, postgres_id ,app):
    spty_track_id = app.search_track(market="PH", song_details=track_details)
    if features := app.get_track_features(spty_track_id):
        features["postgres_id"] = postgres_id
        return features
    else:
        return {'acousticness': None, 
                'danceability': None, 
                'energy': None, 
                'instrumentalness': None, 
                'liveness': None, 
                'loudness': None, 
                'speechiness': None, 
                'tempo': None, 
                'time_signature': None, 
                'valence': None,
                'postgres_id': postgres_id}


def insert_data(track_features, conn, cur):
    try:
        cur.execute("""
                INSERT INTO features (
                    track_id,
                    acousticness,
                    danceability,
                    energy,
                    instrumentalness,
                    liveness,
                    loudness,
                    speechiness,
                    tempo,
                    time_signature,
                    valence
                    ) VALUES (
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s
                    )""", (
                        track_features["postgres_id"],
                        track_features["acousticness"],
                        track_features["danceability"],
                        track_features["energy"],
                        track_features["instrumentalness"],
                        track_features["liveness"],
                        track_features["loudness"],
                        track_features["speechiness"],
                        track_features["tempo"],
                        track_features["time_signature"],
                        track_features["valence"]
                    )
                    )
    except Exception as error:
        print(f"{type(error).__name__}: {error}")
        print("Query:", cur.query)
        conn.rollback()
    else:
        conn.commit()



if __name__ == "__main__":
    start = time.perf_counter()

    # Connection with Postgres and Spotify App
    credentials_path = os.path.join(os.path.dirname(__file__), 'credentials.json')
    with open(credentials_path, 'r') as f:
        credentials = json.load(f)

    conn = psycopg2.connect(dbname=credentials["database"],
                            user=credentials["username"],
                            host=credentials["hostname"],
                            password=credentials["password"])
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    app = spotify_client.SpotifyClient.get_credentials(credentials_path)
    # Run Pipelines
    # beatport_pipeline()
    spotify_pipeline(conn, cur, app)
    

    # Close connection after running script
    cur.close()
    conn.close()

    finish = time.perf_counter()

    print(f"Process finished in {round(finish - start, 2)} seconds")