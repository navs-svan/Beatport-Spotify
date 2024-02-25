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

    search_requests = []


    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = executor.map(search_retrieve, tracks, ids, iter_app)

        for result in results:
            search_requests.append(result)
    
    no_id_list = []
    chunksize = 100
    id_chunks = [search_requests[i:i+chunksize] for i in range(0, len(search_requests), chunksize)]
    for chunk in id_chunks:
        for i, track in enumerate(chunk):
            if track[1] is None:
                no_id_list.append(chunk.pop(i))
        
        # Insert tracks that were not found
        for no_id in no_id_list:
            no_id_features = {"postgres_id" : no_id[0]}
            insert_data(no_id_features, conn, cur)
        # Get track features of tracks that were found then insert them
        
        unzipped = list(zip(*chunk))
        postgres_id_list, track_id_list = unzipped[0], unzipped[1]
        for postgres, feature in zip(postgres_id_list, app.get_track_features(track_id_list)):
            feature['postgres_id'] = postgres
            insert_data(feature, conn, cur)
        

def search_retrieve(track_details, postgres_id ,app):
    sptfy_track_id = app.search_track(market="PH", song_details=track_details)
    return (postgres_id, sptfy_track_id)


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
                        track_features.get("postgres_id"),
                        track_features.get("acousticness", None),
                        track_features.get("danceability", None),
                        track_features.get("energy", None),
                        track_features.get("instrumentalness", None),
                        track_features.get("liveness", None),
                        track_features.get("loudness", None),
                        track_features.get("speechiness", None),
                        track_features.get("tempo", None),
                        track_features.get("time_signature", None),
                        track_features.get("valence", None)
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