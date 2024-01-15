# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
import psycopg2

class BeatportscraperPipeline:
    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        # join artists
        artists = adapter.get("track_artist")
        adapter["track_artist"] = ', '.join(artists)

        # join remixer
        remixers = adapter.get("track_remixer")
        if len(remixers) > 0:
            adapter["track_remixer"] = ', '.join(remixers)
        else:
            adapter["track_remixer"] = 'None'

        return item



class SaveToPostgresPipeline:
    
    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings)
    
    def __init__(self, settings):
        # Start Connection
        hostname = settings.get("POSTGRES_HOSTNAME")
        username = settings.get("POSTGRES_USERNAME")
        password = settings.get("POSTGRES_PASSWORD")
        database = settings.get("POSTGRES_DATABASE")
        
        self.connection = psycopg2.connect(host=hostname, user=username, password=password, database=database)
        self.cur = self.connection.cursor()

        # Create Table
        self.cur.execute(""" 
                CREATE TABLE IF NOT EXISTS tracks(
                id serial PRIMARY KEY,
                chart_name VARCHAR(128),
                chart_date TIMESTAMP,
                track_title VARCHAR(128),
                track_artist VARCHAR(128),
                track_label VARCHAR(128),
                track_remixer VARCHAR(128) DEFAULT NULL,
                track_genre VARCHAR(128),
                track_bpm SMALLINT,
                track_key VARCHAR(128),
                track_date DATE,
                track_length_ms INTEGER
            )              
            """)


    def process_item(self, item, spider):
        self.cur.execute("""INSERT INTO tracks (
                         chart_name,
                         chart_date,
                         track_title,
                         track_artist,
                         track_label,
                         track_remixer,
                         track_genre,
                         track_bpm,
                         track_key,
                         track_date,
                         track_length_ms 
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
                         item["chart_name"],
                         item["chart_date"],
                         item["track_title"],
                         item["track_artist"],
                         item["track_label"],
                         item["track_remixer"],
                         item["track_genre"],
                         item["track_bpm"],
                         item["track_key"],
                         item["track_date"],
                         item["track_length_ms"]

                        ))

        self.connection.commit()
        return item

    def close_spider(self, spider):
        self.cur.close()
        self.connection.close()