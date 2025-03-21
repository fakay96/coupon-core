import scrapy
from scrapy_splash import SplashRequest
from discountscraper.items import DiscountItem
import logging
from urllib.parse import urljoin

class DiscountSpider(scrapy.Spider):
    name = 'discountspider'
    allowed_domains = ['fromaustria.com']
    start_urls = ['https://www.fromaustria.com/de-AT/angebote']
    
    lua_script = """
    function main(splash, args)
        -- Set German language and viewport
        splash:set_viewport_size(1920, 1080)
        splash:set_user_agent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        splash:set_custom_headers({
            ['Accept-Language'] = 'de-DE,de;q=0.9,en;q=0.8'
        })
        splash.private_mode_enabled = false
        
        -- Go to URL
        assert(splash:go(args.url))
        assert(splash:wait(3))
        
        -- Handle cookie consent
        local consent_button = splash:select('button[data-testid="uc-accept-all-button"]')
        if consent_button then
            consent_button:mouse_click()
            splash:wait(2)
        end
        
        -- Initial wait for products to load
        splash:wait(2)
        
        -- Scroll simulation with dynamic content loading
        for i = 1, 8 do  -- Increased scroll iterations
            splash:evaljs([[
                window.scrollTo({
                    top: document.body.scrollHeight * ]] .. i .. [[/ 8,
                    behavior: 'smooth'
                });
            ]])
            splash:wait(1.5)  -- Increased wait time between scrolls
        end
        
        -- Final wait for all content
        splash:wait(3)
        
        -- Check for next button
        local next_button = splash:select('button.pagination__btn--next')
        local has_next = next_button ~= nil and not next_button:hasClass('disabled')
        
        -- Click next if requested
        if args.click_next and has_next then
            next_button:mouse_click()
            splash:wait(3)
            
            -- Scroll new page
            for i = 1, 8 do
                splash:evaljs([[
                    window.scrollTo({
                        top: document.body.scrollHeight * ]] .. i .. [[/ 8,
                        behavior: 'smooth'
                    });
                ]])
                splash:wait(1.5)
            end
            splash:wait(3)
        end
        
        return {
            html = splash:html(),
            has_next = has_next,
            cookies = splash:get_cookies(),
            url = splash:url()
        }
    end
    """
    
    def start_requests(self):
        for url in self.start_urls:
            yield SplashRequest(
                url=url,
                callback=self.parse,
                endpoint='execute',
                args={
                    'lua_source': self.lua_script,
                    'wait': 3,
                    'timeout': 90,
                    'click_next': False
                },
                dont_filter=True,
                meta={'page': 1}
            )
    
    def parse(self, response):
        try:
            current_page = response.meta.get('page', 1)
            self.logger.info(f"Parsing page {current_page}: {response.url}")
            
            # Updated selector to catch all product cards
            products = response.css('div.productGrid li.productCard')
            self.logger.info(f"Found {len(products)} products on page {current_page}")
            
            for product in products:
                item = DiscountItem()
                
                # Enhanced selectors with better text extraction
                item['brand'] = self.clean_text(product.css('.productCard__brand::text').get())
                item['name'] = self.clean_text(product.css('.productCard__title a.productCard__link::text').get())
                
                # Price handling with currency
                sale_price = product.css('.productCard__price .price--reduced::text').get()
                original_price = product.css('.productCard__price .instead-price::text').get()
                
                if sale_price:
                    item['sale_price'] = self.format_price(sale_price)
                if original_price:
                    item['original_price'] = self.format_price(original_price)
                
                # Additional fields
                item['price_per_unit'] = self.format_price(
                    product.css('.productCard__price .price--perUnit::text').get()
                )
                item['discount_percentage'] = self.extract_discount(
                    product.css('.productCard__tags .flag.sale-tag.small.percent::text').get()
                )
                item['stock_info'] = self.clean_text(
                    product.css('.productCard__stock::text').get()
                )
                
                # Category extraction
                category = response.css('nav.breadcrumb span[itemprop="name"]::text').getall()
                item['category'] = ' > '.join([cat.strip() for cat in category if cat.strip()])
                
                # URL handling
                product_url = product.css('.productCard__title a.productCard__link::attr(href)').get()
                if product_url:
                    item['url'] = urljoin(response.url, product_url)
                
                # Only yield items with a discount
                if item['sale_price'] and item['original_price'] and item['discount_percentage']:
                    yield item
            
            # Pagination handling
            has_next = response.data.get('has_next', False)
            if has_next and current_page < 20:  # Increased page limit
                self.logger.info(f"Following next page {current_page + 1}")
                yield SplashRequest(
                    url=response.url,
                    callback=self.parse,
                    endpoint='execute',
                    args={
                        'lua_source': self.lua_script,
                        'wait': 3,
                        'timeout': 90,
                        'click_next': True,
                        'cookies': response.data.get('cookies', [])
                    },
                    dont_filter=True,
                    meta={'page': current_page + 1}
                )
            
        except Exception as e:
            self.logger.error(f"Error parsing page {response.url}: {str(e)}")
    
    def clean_text(self, text):
        """Clean and normalize text content"""
        if text:
            return ' '.join(text.strip().split())
        return None
    
    def format_price(self, price):
        """Format price with currency symbol"""
        if not price:
            return None
        try:
            # Remove any existing currency symbols and convert to float
            clean_price = price.replace('€', '').replace(',', '.').strip()
            return f"€{float(clean_price):.2f}"
        except (ValueError, TypeError):
            return None
    
    def extract_discount(self, discount):
        """Extract and format discount percentage"""
        if not discount:
            return None
        try:
            # Remove % and - signs, convert to integer
            clean_discount = discount.replace('%', '').replace('-', '').strip()
            return int(clean_discount)
        except (ValueError, TypeError):
            return None