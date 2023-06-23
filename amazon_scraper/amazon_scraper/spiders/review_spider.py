import scrapy
from urllib.parse import urljoin
import re
import pandas as pd
from tqdm import tqdm


class ReviewSpiderSpider(scrapy.Spider):

    name = 'review_spider'

    custom_settings = {
        'LOG_LEVEL': 'ERROR',
        'FEEDS': {
            'data/review_data.csv':
                {'format': 'csv',
                 'overwrite': True,
                 },
        }
    }

    REVIEW_PAGE_LIMIT = 15

    asin_df = pd.read_csv('data/asin_data.csv')
    asin_list = list(asin_df['asin'])

    def start_requests(self):

        for asin in self.asin_list:
            review_page_num = 0
            progress_bar = tqdm(total=self.REVIEW_PAGE_LIMIT,
                                desc=asin,
                                bar_format='{l_bar}{bar:20}{r_bar}{bar:-10b}')

            amazon_reviews_url = f'https://www.amazon.com/product-reviews/{asin}/'
            yield scrapy.Request(url=amazon_reviews_url,
                                 callback=self.parse_reviews,
                                 meta={'asin': asin,
                                       'review_page_num': review_page_num,
                                       'progress_bar': progress_bar})

    def parse_reviews(self, response):

        asin = response.meta['asin']
        review_page_num = response.meta['review_page_num']
        progress_bar = response.meta['progress_bar']

        review_page_num += 1
        progress_bar.update(1)

        # Get next page url
        next_page_relative_url = response.css(".a-pagination .a-last>a::attr(href)").get()

        if next_page_relative_url is not None and review_page_num < self.REVIEW_PAGE_LIMIT:

            joined_url = urljoin('https://www.amazon.com/', next_page_relative_url)

            # Parse the url to avoid login detection
            if 'signin' in joined_url:
                product_id = re.search('product-reviews%2F(.*?)%3', joined_url).group(1)
                page_number = re.search('pageNumber%3D(.*?)&', joined_url).group(1)
                base_url = 'https://www.amazon.com/product-reviews/'
                next_url = f'{base_url}{product_id}/ref=cm_cr_arp_d_paging_btm_next_{page_number}?pageNumber={page_number}'
            else:
                next_url = joined_url

            yield scrapy.Request(url=next_url,
                                 callback=self.parse_reviews,
                                 meta={'asin': asin,
                                       'review_page_num': review_page_num,
                                       'progress_bar': progress_bar})
        else:
            # progress_bar.update(progress_bar.total-review_page_num)
            progress_bar.total = review_page_num

        # Parse Product Reviews
        review_elements = response.css('#cm_cr-review_list div.review')
        for review_element in review_elements:
            yield {
                'asin': asin,
                'text': ''.join(review_element.css('span[data-hook=review-body] ::text').getall()).strip(),
                'title': review_element.css('*[data-hook=review-title]>span::text').get(),
                'location_and_date': review_element.css('span[data-hook=review-date] ::text').get(),
                'verified': bool(review_element.css('span[data-hook=avp-badge] ::text').get()),
                'rating': review_element.css('*[data-hook*=review-star-rating] ::text').re(r'(\d+\.*\d*) out')[0],
            }