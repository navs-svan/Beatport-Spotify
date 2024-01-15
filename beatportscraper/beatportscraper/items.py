# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class ChartItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    chart_name = scrapy.Field()
    chart_date = scrapy.Field()
    track_title = scrapy.Field()
    track_artist = scrapy.Field()
    track_label = scrapy.Field()
    track_remixer = scrapy.Field()
    track_genre = scrapy.Field()
    track_bpm = scrapy.Field()
    track_key = scrapy.Field()
    track_date = scrapy.Field()
    

    pass
