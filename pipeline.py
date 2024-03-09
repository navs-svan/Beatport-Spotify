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
    """
    Summary: Pipeline of the scrapy spider using CrawlerProcess.
        It imports the beatportscraper spider and its settings.
    """
    settings = get_project_settings()
    process = CrawlerProcess(settings)
    process.crawl(BeatportspiderSpider)
    process.start()


def spotify_pipeline(
    conn: psycopg2.extensions.connection,
    cur: psycopg2.extras.RealDictCursor,
    app: spotify_client.SpotifyClient,
) -> None:
    """
    Summary: Pipeline of the spotify API. It retrieves records of track title
        and track artist from the Postgres database and retrieves their audio features.
        These are subsequently stored in the same database. If the track is not found,
        or no audio features are found, then the rows stored in the table will contain
        null values.

    Args:
        conn (psycopg2.extensions.connection): A psycopg2 connection class.
        cur (psycopg2.extensions.RealDictCursor): A pscyopg2 dictionary-like cursor.
            The attributes of the retrieved records from queries can be accessed
            similar to Python dictionaries.
        app (spotify_client.SpotifyClient): A spotify_client SpotifyCLient class.
    """
    cur.execute(
        """ 
            CREATE TABLE IF NOT EXISTS features(
                track_title VARCHAR(128) NOT NULL,
				track_artist VARCHAR(128) NOT NULL,
                track_year DATE NOT NULL,
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
				UNIQUE(track_title, track_artist),
				PRIMARY KEY(track_title, track_artist, track_year)
            );              
        """
    )
    get_query = """
                SELECT DISTINCT 
                t.track_title as title,
                t.track_artist as artist,
                t.track_date AS year 
                FROM tracks t 
                WHERE NOT EXISTS (
                    SELECT 
                        f.track_artist,
                        f.track_title
                    FROM features f 
                    WHERE t.track_artist = f.track_artist
                    AND t.track_title = f.track_title
                    AND t.track_date = f.track_year)
                LIMIT 1000;
             """
    # results are limited to 1000 because of the possibility of soft ban due to large number of requests

    cur.execute(get_query)
    tracks = cur.fetchall()

    titles = [track["title"] for track in tracks]
    artists = [track["artist"] for track in tracks]
    years = [track["year"] for track in tracks]

    iter_app = itertools.repeat(app)

    search_requests = []

    # Search endpoint is somewhat more lenient to large number of requests than track features
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = executor.map(search_retrieve, tracks, iter_app)

        for result in results:
            search_requests.append(result)

    chunksize = 100
    id_chunks = [
        search_requests[i : i + chunksize]
        for i in range(0, len(search_requests), chunksize)
    ]

    for chunk in id_chunks:
        no_id_list = []
        for i, track in enumerate(chunk):
            if track[3] is None:
                no_id_list.append(chunk[i])

        chunk = [track for track in chunk if track not in no_id_list]

        # Insert tracks that were not found
        for no_id in no_id_list:
            no_id_features = {
                "postgres_title": no_id[0],
                "postgres_artist": no_id[1],
                "postgres_year": no_id[2],
            }
            insert_data(no_id_features, conn, cur)

        # Get track features of tracks that were found then insert them
        unzipped = list(zip(*chunk))
        postgres_titles, postgres_artists, postgres_years, track_id_list = (
            unzipped[0],
            unzipped[1],
            unzipped[2],
            unzipped[3],
        )
        for title, artist, year, feature in zip(
            postgres_titles,
            postgres_artists,
            postgres_years,
            app.get_track_features(track_id_list),
        ):
            feature["postgres_title"] = title
            feature["postgres_artist"] = artist
            feature["postgres_year"] = year
            insert_data(feature, conn, cur)


def search_retrieve(
    track_details: dict,
    app: spotify_client.SpotifyClient,
) -> tuple:
    """
    Summary: Searches tracks through the SpotifyClient.search_track function.

    Args:
        track_details (dict): a dictionary containing the values of
            "title", "year", and "artist".
        app (spotify_client.SpotifyClient): A spotify_client SpotifyCLient class.

    Returns:
        tuple: A tuple containing the track title, track artist, track year,
            and Spotify track ID
    """
    sptfy_track_id = app.search_track(market="PH", song_details=track_details)
    return (
        track_details["title"],
        track_details["artist"],
        track_details["year"],
        sptfy_track_id,
    )


def insert_data(
    track_features: dict,
    conn: psycopg2.extensions.connection,
    cur: psycopg2.extras.RealDictCursor,
) -> None:
    """
    Summary: Inserts the audio features into the Postgres database

    Args:
        track_features (dict): a dictionary containing the audio features
        conn (psycopg2.extensions.connection): A psycopg2 connection class.
        cur (psycopg2.extensions.RealDictCursor): A pscyopg2 dictionary-like cursor.
            The attributes of the retrieved records from queries can be accessed
            similar to Python dictionaries.
    """
    try:
        cur.execute(
            """
                INSERT INTO features (
                    track_title,
                    track_artist,
                    track_year,
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
                        %s,
                        %s,
                        %s
                    )""",
            (
                track_features.get("postgres_title"),
                track_features.get("postgres_artist"),
                track_features.get("postgres_year"),
                track_features.get("acousticness", None),
                track_features.get("danceability", None),
                track_features.get("energy", None),
                track_features.get("instrumentalness", None),
                track_features.get("liveness", None),
                track_features.get("loudness", None),
                track_features.get("speechiness", None),
                track_features.get("tempo", None),
                track_features.get("time_signature", None),
                track_features.get("valence", None),
            ),
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
    credentials_path = os.path.join(os.path.dirname(__file__), "credentials.json")
    with open(credentials_path, "r") as f:
        credentials = json.load(f)

    conn = psycopg2.connect(
        dbname=credentials["database"],
        user=credentials["username"],
        host=credentials["hostname"],
        password=credentials["password"],
    )
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    app = spotify_client.SpotifyClient.get_credentials(credentials_path)

    # Run Pipelines
    beatport_pipeline()
    spotify_pipeline(conn, cur, app)

    # Close connection after running script
    cur.close()
    conn.close()

    finish = time.perf_counter()

    print(f"Process finished in {round(finish - start, 2)} seconds")
