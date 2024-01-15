from typing import Iterable
import scrapy
from scrapy.http import Request
from beatportscraper.items import ChartItem


class BeatportspiderSpider(scrapy.Spider):
    name = "beatportspider"
    allowed_domains = ["www.beatport.com"]
    start_urls = ["https://www.beatport.com/charts/all?page=1&per_page=150"]


    def parse(self, response):
        charts = response.css('div.fOQOHN')
        for chart in charts:
            relative_url = chart.css('a.artwork::attr(href)').get()
            chart_url = 'https://www.beatport.com' + relative_url
            yield response.follow(chart_url, callback=self.parse_charts)


        xpath_string = """
                        //div[@class='Pager-style__Container-sc-47555d13-6 kYSUOG pages']/
                        div[@class='Pager-style__PageNavItems-sc-47555d13-0 dkbnEZ']/
                        a[@class='Pager-style__Page-sc-47555d13-1 iMEhSh active']/
                        following::a/@href
                    """
        next_page = response.xpath(xpath_string).get()
        print(f"**********{next_page}************")
        if next_page is not None:
            next_page_url = 'https://www.beatport.com' + next_page
            yield response.follow(next_page_url, callback=self.parse)

    
    def parse_charts(self, response):
        chart_items = ChartItem()
        yield chart_items

