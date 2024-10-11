from typing import Iterable
import scrapy
from scrapy.http import Request
from beatportscraper.items import ChartItem
import json


class BeatportspiderSpider(scrapy.Spider):
    name = "beatportspider"
    allowed_domains = ["www.beatport.com"]
    start_urls = ["https://www.beatport.com/charts/all?page=1&per_page=150"]

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings)
    
    def __init__(self, settings):
        ...
        
    def parse(self, response):
        charts = response.css('div.iUxUui')
        for chart in charts:
            relative_url = chart.css('a.artwork::attr(href)').get()
            chart_url = 'https://www.beatport.com' + relative_url
            yield response.follow(chart_url, callback=self.parse_charts)

        xpath_string = """
                        //div[@class='Pager-style__Container-sc-47555d13-6 dGgBuJ pages']/
                        div[@class='Pager-style__PageNavItems-sc-47555d13-0 iqjXbu']/
                        a[@class='Pager-style__Page-sc-47555d13-1 hnjacC active']/
                        following::a/@href
                    """
        next_page = response.xpath(xpath_string).get()
        print(f"**********{next_page}************")
        if next_page is not None:
            next_page_url = 'https://www.beatport.com' + next_page
            yield response.follow(next_page_url, callback=self.parse)

    
    def parse_charts(self, response):
        chart_items = ChartItem()
        script_tag = response.css('script#__NEXT_DATA__::text').get()
        json_blob = json.loads(script_tag)
        tracks = json_blob["props"]["pageProps"]["dehydratedState"]["queries"][1]["state"]["data"]["results"]
        chart = json_blob["props"]["pageProps"]["dehydratedState"]["queries"][0]["state"]["data"]
        for track in tracks:
            chart_items = ChartItem()
            remixer_list = []
            artist_list = []
            chart_items["chart_url"] = response.url
            chart_items["chart_name"] = chart["name"]
            chart_items["chart_date"] = chart["publish_date"]
            chart_items["chart_author"] = chart["person"]["owner_name"]
            chart_items["track_title"] = track["name"]
            chart_items["track_label"] = track["release"]["label"]["name"]

            for artist in track["artists"]:
                artist_list.append(artist["name"])
            chart_items["track_artist"] = artist_list

            try:
                for remixer in track["remixers"]:
                    remixer_list.append(remixer["name"])
                chart_items["track_remixer"] = remixer_list
            except KeyError:
                chart_items["track_remixer"] = None

            chart_items["track_genre"] = track["genre"]["name"]
            chart_items["track_bpm"] = track["bpm"]

            try:
                chart_items["track_key"] = track["key"]["name"]
            except TypeError:
                chart_items["track_key"] = None

            chart_items["track_date"] = track["publish_date"]
            chart_items["track_length_ms"] = track["length_ms"]

            yield chart_items
