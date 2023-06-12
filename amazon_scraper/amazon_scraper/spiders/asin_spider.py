import scrapy
from urllib.parse import urljoin
from tqdm import tqdm


class AsinSpiderSpider(scrapy.Spider):

    name = 'asin_spider'

    custom_settings = {
        'LOG_LEVEL': 'ERROR',
        'FEEDS': {
            'data/asin_data.csv':
                {'format': 'csv',
                 'overwrite': True,
                 },
        }
    }

    ASIN_PAGE_LIMIT = 10
    cate_list = ['keyboard', 'monitor', 'mouse', 'earphone']

    def start_requests(self):

        for cate in self.cate_list:
            asin_page_num = 0
            progress_bar = tqdm(total=self.ASIN_PAGE_LIMIT,
                                desc=cate,
                                bar_format='{l_bar}{bar:20}{r_bar}{bar:-10b}')

            amazon_cate_url = f'https://www.amazon.com/s?k={cate}'

            yield scrapy.Request(url=amazon_cate_url,
                                 callback=self.get_id,
                                 meta={'cate': cate,
                                       'asin_page_num': asin_page_num,
                                       'progress_bar': progress_bar})

    def get_id(self, response):

        cate = response.meta['cate']
        asin_page_num = response.meta['asin_page_num']
        progress_bar = response.meta['progress_bar']

        asin_page_num += 1
        progress_bar.update(1)

        # Get next page url
        next_page_relative_url = response.css(
            '.a-section.a-text-center.s-pagination-container .s-pagination-strip > a:last-of-type::attr(href)'
        ).get()

        if next_page_relative_url is not None and asin_page_num < self.ASIN_PAGE_LIMIT:
            next_url = urljoin('https://www.amazon.com/', next_page_relative_url)
            yield scrapy.Request(url=next_url,
                                 callback=self.get_id,
                                 meta={'cate': cate,
                                       'asin_page_num': asin_page_num,
                                       'progress_bar': progress_bar})

        productid_elements_raw = response.css(
            'div.s-main-slot.s-result-list.s-search-results.sg-row > div::attr(data-asin)'
        ).getall()
        productid_elements = [item for item in productid_elements_raw if item != '']
        for productid_element in productid_elements:
            yield {
                'category': cate,
                'asin': productid_element
            }