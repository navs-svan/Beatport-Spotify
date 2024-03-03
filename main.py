import src.spotify_client as spotify_client
import psycopg2
import psycopg2.extras
import os
import json
import argparse
import random
from collections.abc import Generator


def by_chart(cur: psycopg2.extras.RealDictCursor, chart_details: tuple) -> tuple:
    """
    Summary: Retrieves the contents of a specific chart data from a Postgres database

    Args:
        cur (psycopg2.extensions.RealDictCursor): A pscyopg2 dictionary-like cursor.
            The attributes of the retrieved records from queries can be accessed
            similar to Python dictionaries.
        chart_details (tuple): a tuple containing the (chart name, chart author)

    Returns:
        tuple: returns a tuple (list, str). The first item (list) contains the
            details [title, artist, year] of each track in the specified chart. The
            second item (str) is a string literal of the playlist title that will
            be supplied to the Spotify API.
    """
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


def by_artist(
    cur: psycopg2.extras.RealDictCursor,
    artist: str,
    limit: int = 50,
    month_range: list = None,
) -> tuple:
    """
    Summary: Retrieves tracks made by a specific artist from a Postgres database.
        The retrieved records can be limited by a range of months.

    Args:
        cur (psycopg2.extensions.RealDictCursor): A pscyopg2 dictionary-like cursor.
            The attributes of the retrieved records from queries can be accessed similar
            to Python dictionaries.
        artist (str): string literal of the specified artist.
        limit (int): number of tracks to be retrieved. Has no max value.
        month_range (list): a list containing the string literals of the bounding
            months [20YY-MM, 20YY-MM].

    Returns:
        tuple: returns a tuple (list, str). The first item (list) contains the
            details [title, artist, year] of each track in the specified artist.
            The second item (str) is a string literal of the playlist title that
            will be supplied to the Spotify API.
    """
    # SQL query
    if month_range:
        query = """
                    SELECT 
                        DISTINCT track_title as title, 
                        track_artist as artist,
                        EXTRACT('Year' FROM track_date) AS year
                    FROM tracks
                    WHERE strpos(track_artist, %s) > 0
                    AND track_date BETWEEN %s AND %s;
                """
        cur.execute(query, (artist, f"{month_range[0]}-01", f"{month_range[1]}-31"))
    else:
        query = """
                    SELECT 
                        DISTINCT track_title AS title, 
                        track_artist AS artist,
                        EXTRACT('Year' FROM track_date) AS year
                    FROM tracks
                    WHERE strpos(track_artist, %s) > 0;
                """
        cur.execute(query, (artist,))

    tracks = cur.fetchall()

    try:
        limited_tracks = random.sample(tracks, limit)
    except ValueError:
        limited_tracks = tracks

    title = f"Tracks by {tracks[0]['artist']}"

    return (limited_tracks, title)


def by_genre(
    cur: psycopg2.extras.RealDictCursor,
    genre: str,
    limit: int = 50,
    mode: str = "top",
    month_range: list = None,
) -> tuple:
    """
    Summary: Retrieves tracks of a certain genre from a Postgres database.
        The retrieved records can be limited by a range of months. Records can
        be further sorted by number of appearances in charts or randomly

    Args:
        cur (psycopg2.extensions.RealDictCursor): A pscyopg2 dictionary-like cursor.
            The attributes of the retrieved records from queries can be accessed
            similar to Python dictionaries.
        genre (str): string literal of the specified genre.
        limit (int): number of tracks to be retrieved. Has no max value.
        mode (str): "top" sorts the records by chart appearances. "random" sorts
            the records in random
        month_range (list): a list containing the string literals of the bounding
            months [20YY-MM, 20YY-MM].

    Returns:
        tuple: returns a tuple (list, str). The first item (list) contains the
            details [title, artist, year] of each track in the specified artist.
            The second item (str) is a string literal of the playlist title that
            will be supplied to the Spotify API.
    """
    # SQL query
    if month_range:
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
        cur.execute(query, (genre, f"{month_range[0]}-01", f"{month_range[1]}-31"))
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


def by_author(
    cur: psycopg2.extras.RealDictCursor, chart_author: str
) -> Generator[tuple, None, None]:
    """
    Summary: Retrieves all charts of a specified chart author from a Postgres database.

    Args:
        cur (psycopg2.extensions.RealDictCursor): A pscyopg2 dictionary-like cursor.
            The attributes of the retrieved records from queries can be accessed
            similar to Python dictionaries.
        genre (str): string literal of the specified chart author.

    Yields:
        tuple: returns a tuple (str, str). The first item contains the chart name while 
            the second items contains the chart author name
    """
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


if __name__ == "__main__":
    # INITIALIZE PARSER
    global_parser = argparse.ArgumentParser(
        prog="main", description="Create playlists in Spotify"
    )

    # ADD PARAMETERS

    subparser = global_parser.add_subparsers(
        title="subcommands",
        required=True,
        dest="command",
        help="Methods of creating a playlist",
    )

    # chart subparser
    chart_parser = subparser.add_parser(
        "chart", help="Creates a playlist based on the specified chart"
    )
    chart_parser.add_argument(
        "-t", "--title", type=str, required=True, help="Title of beatport chart"
    )
    chart_parser.add_argument(
        "-a", "--author", type=str, required=True, help="Author of beatport chart"
    )

    # author subparser
    author_parser = subparser.add_parser(
        "author", help="Creates playlists of all charts made by the specified author"
    )
    author_parser.add_argument(
        "-a", "--author", type=str, required=True, help="Author of beatport chart"
    )
    
    # artist subparser
    artist_parser = subparser.add_parser(
        "artist", help="Creates a playlist based on tracks of the specified artist"
    )
    artist_parser.add_argument(
        "-a", "--artist", type=str, required=True, help="Specified artist of tracks"
    )
    artist_parser.add_argument(
        "-l", "--limit", default=50, type=int, help="Number of tracks to be added"
    )
    artist_parser.add_argument(
        "-y",
        "--years",
        type=str,
        nargs=2,
        help='Range of dates to consider. Format: "YYYY-MM YYYY-MM"',
    )
    
    # genre subparser
    genre_parser = subparser.add_parser(
        "genre", help="Creates a playlist based on the specified genre"
    )
    genre_parser.add_argument(
        "-a", "--genre", type=str, required=True, help="Specified track genre"
    )
    genre_parser.add_argument(
        "-l", "--limit", default=50, type=int, help="Number of tracks to be added"
    )
    genre_parser.add_argument(
        "-y",
        "--years",
        type=str,
        nargs=2,
        help='Range of dates to consider. Format: "YYYY-MM YYYY-MM"',
    )
    genre_parser.add_argument(
        "-m",
        "--mode",
        type=str,
        default="top",
        choices=["top", "random"],
        help="Mode of choosing tracks (Top songs or Random songs)",
    )

    global_parser.add_argument(
        "-r",
        "--recommend",
        dest="recommendation",
        action="store_true",
        help="Creates a playlist from recommendations based on tracks that should have been originally added",
    )

    # PARSE ARGUMENTS
    args = global_parser.parse_args()

    # Postgres Connection
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

    # BODY
    track_title_list = []

    match args.command:
        case "chart":
            chart_details = (args.title, args.author)
            track_title_list = [by_chart(cur=cur, chart_details=chart_details)]
        case "author":
            chart_details = by_author(cur=cur, chart_author=args.author)
            for chart_detail in chart_details:
                tracks, title = by_chart(cur=cur, chart_details=chart_detail)
                track_title_list.append((tracks, title))
        case "artist":
            track_title_list = [
                by_artist(
                    cur=cur,
                    artist=args.artist,
                    limit=args.limit,
                    month_range=args.years,
                )
            ]
        case "genre":
            track_title_list = [
                by_genre(
                    cur,
                    genre=args.genre,
                    limit=args.limit,
                    mode=args.mode,
                    month_range=args.years,
                )
            ]

    # Spotify API
    app = spotify_client.SpotifyClient.get_credentials(credentials_path)

    for track_title in track_title_list:
        track_id_list = []
        tracks, title = track_title[0], track_title[1]

        for track in tracks:
            if track_id := app.search_track(market="PH", song_details=track):
                track_id_list.append(track_id)

        if args.recommendation is True:
            reco_track_ids = app.get_recommendations(
                market="PH", track_ids=track_id_list, limit=30
            )
            title = title + " (recommendations)"
            playlist_id = app.create_playlist(
                title, "Playlist created through Spotify API"
            )
            app.add_track(playlist_id=playlist_id, track_id_list=reco_track_ids)
        else:
            playlist_id = app.create_playlist(
                title, "Playlist created through Spotify API"
            )
            app.add_track(playlist_id=playlist_id, track_id_list=track_id_list)

    # Close connection after running script
    cur.close()
    conn.close()
