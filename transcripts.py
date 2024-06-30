import scrapy
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
import openpyxl
from urllib.parse import urlparse
from scrapy.exceptions import IgnoreRequest
from scrapy import signals
from scrapy.exceptions import NotConfigured


class RobotsTxtMiddleware:
    def __init__(self, crawler):
        self.crawler = crawler

    @classmethod
    def from_crawler(cls, crawler):
        if not crawler.settings.getbool('ROBOTSTXT_OBEY'):
            raise NotConfigured
        o = cls(crawler)
        crawler.signals.connect(o.spider_opened, signal=signals.spider_opened)
        return o

    def process_request(self, request, spider):
        if not hasattr(spider, 'robot_parser'):
            return None

        if not spider.robot_parser.allowed(request.url, '*'):
            spider.logger.info(f"Blocked by robots.txt: {request.url}")
            raise IgnoreRequest(f"Blocked by robots.txt: {request.url}")

    def spider_opened(self, spider):
        spider.robot_parser = self.get_robot_parser(spider)

    def get_robot_parser(self, spider):
        rp = spider.settings.get('ROBOTSTXT_PARSER', 'scrapy.robotstxt.ProtegoRobotParser')
        if rp == 'scrapy.robotstxt.ProtegoRobotParser':
            return self.from_crawler(self.crawler)
        elif rp == 'scrapy.robotstxt.BasicRobotParser':
            from scrapy.robotstxt import BasicRobotParser
            return BasicRobotParser.from_crawler(self.crawler)
        else:
            return None


class URLCrawler(CrawlSpider):
    name = 'url-crawler'
    domain = ['tinthethao.com.vn']
    start_urls = [
        'https://www.tinthethao.com.vn']
    max_pages_per_domain = 400
    current_pages = 0
    allowed_domains = domain
    urls = set()
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp'}
    rules = (
        Rule(LinkExtractor(allow_domains=allowed_domains, deny_extensions=image_extensions),
             callback='parse_item', follow=True),
    )

    custom_settings = {
        'ROBOTSTXT_OBEY': True,
    }

    # def parse_item(self, response):
    #     if self.current_pages < self.max_pages_per_domain:
    #         self.current_pages += 1
    #         self.urls.add(response.url)
    #         self.log(f"Scraped URL: {response.url}, Total URLs: {len(self.urls)}")
    #
    #         # Integrate the parse method here
    #         for item in response.css('h3') or response.css('div.h-full') or response.css(
    #                 'div.box-content-music-list') or response.css('h1'):
    #             if self.current_pages <= self.max_pages_per_domain:
    #                 next_page_url = item.css('a::attr(href)').get()
    #                 if next_page_url:
    #                     if (next_page_url not in self.urls):
    #                         self.urls.add(next_page_url)
    #                         self.current_pages = len(self.urls)
    #                         yield response.follow(next_page_url, callback=self.parse_item)
    #
    #     else:
    #         if self.urls:
    #             self.save_urls_to_excel(list(self.urls))
    #             self.log(f"Reached the limit of {self.max_pages_per_domain} pages. Stopping.")
    #             self.crawler.engine.close_spider(self, f'Reached limit of {self.max_pages_per_domain} pages')
    def parse_item(self, response):
        if self.current_pages < self.max_pages_per_domain:
            self.current_pages += 1
            self.urls.add(response.url)
            self.log(f"Scraped URL: {response.url}, Total URLs: {len(self.urls)}")

            # Lấy tất cả các liên kết (thẻ a) trên trang
            all_links = response.css('a::attr(href)').getall()
            for link in all_links:
                # Kiểm tra điều kiện để lọc các liên kết không mong muốn
                if link and link.startswith('http'):
                    if link not in self.urls:
                        self.urls.add(link)
                        self.current_pages = len(self.urls)
                        yield response.follow(link, callback=self.parse_item)
        else:
            if self.urls:
                self.save_urls_to_excel(list(self.urls))
                self.log(f"Reached the limit of {self.max_pages_per_domain} pages. Stopping.")
                self.crawler.engine.close_spider(self, f'Reached limit of {self.max_pages_per_domain} pages')

    def closed(self, reason):
        if self.urls:
            self.save_urls_to_excel(list(self.urls))

    def save_urls_to_excel(self, urls):
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.title = 'URLs'
        sheet.append(['url'])

        for url in urls:
            sheet.append([url])

        domain_name = self.domain[0].split('.')[0]
        file_name = f"urls_summary_{domain_name}.xlsx"
        workbook.save(file_name)
        self.log(f"Saved {len(urls)} URLs to {file_name}")


if __name__ == "__main__":
    from scrapy.crawler import CrawlerProcess

    process = CrawlerProcess(settings={
        "FEEDS": {
            "items.json": {"format": "json"},
        }
    })

    process.crawl(URLCrawler)
    process.start()
