from dataclasses import dataclass, field
import re
from typing import Dict, List
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup
import requests
from utils.logging_config import setup_logging, load_config

logger = setup_logging()
web_config = load_config("webs_config.yml")

@dataclass 
class ProductInfo:
    
	# metadata 
	product_name: str
	product_url: str
	website_name: str 
	original_category: List[str] = field(default_factory=list)
 
	product_image: List[str] = field(default_factory=list)
	product_image_type: int = 1 
 
	product_code: str = "" # sku 
	product_description: str = ""
	product_unit_price: int = 0
	product_currency: str="VND"
	product_discount_percentage: float = 0.0
	product_total_orders: int = 10
	product_stock_quantity: int = 50
	product_total_ratings: int = 0
	product_overall_stars: float = 0.0
	
	product_image_name: str = ""

class ProductExtractor: 
	""" 
 	Extract products for both pagination and progressive loading techniques
  	"""

	def __init__(self, websites_config: Dict, website_name: str):
		self.website_config = websites_config.get(website_name, {}) 
		self.website_name = website_name
		self.scraping_config = self.website_config.get('scraping', {})
	
	def process_pages(self, category_url: str) -> List[ProductInfo]:
		logger.info(f"Extracting products from: ({category_url})")
		logger.debug(f"Website config: {self.website_config}")
		logger.debug(f"Scraping config: {self.scraping_config}")
		logger.debug(f"Loading type: {self.scraping_config.get('loading_type', 'single-page')}")
    
		all_products = []
		current_page = category_url # first page 

		loading_type = self.scraping_config.get('loading_type', 'single-page')
		
		if loading_type == "pagination":
			all_products = self._crawl_pagination(current_page, self.website_config)
		elif loading_type == "single-page":
			pass
		elif loading_type == "progressive":
			pass
		
		logger.info(f"Products count: {len(all_products) if all_products else 0}")
		return all_products
		
	def _crawl_pagination(self, url: str) -> List[ProductInfo]:
		products = []
		next_selector = self.scraping_config["pagination"]["next_selector"]
		page_count = 1
 
		logger.info("Start pagination crawling ...")
		logger.debug(f"Next selector: {next_selector}")
 
		while url:
			try:
				logger.info(f"Crawling page {page_count} in {url}")
				req = Request(
        			url, 
           			headers={"User-Agent": web_config["http"]["user_agent"]}
              	)
     
				html = urlopen(req)
				bs = BeautifulSoup(html, "html.parser")
				
				product_tag = self.scraping_config["product_tag"]
				product_selector = self.scraping_config["product_selector"]
				product_cards = bs.find_all(
	       			product_tag, 
	          		class_=re.compile(product_selector.replace(".", ""))
	            )

				for card in product_cards:
					logger.info("Checkpoint!")
					
					product_url = card.get('href')
					logger.debug(f"Product url: {product_url}")
     
					# make url absolute if it's relative 
					if not product_url.startswith('https://'):
						website_path = self.website_config["path"]["website_path"]
						website_path = website_path.rstrip('/')
						product_url = urljoin(website_path, product_url)

					# get detailed product info 
					# logger.info("Checkpoint!")
					product = self._extract_product_details(product_url)
					if product: 
						products.append(product)

			except Exception as e:
				logger.error(f"Error occured when extracting product details")
				return None

			else:
				# find next page link 
				next_page = bs.select_one(next_selector)
				url = next_page.get('href') if next_page else None 
				page_count += 1
    
		return products

	def crawl_loadmore(self, url: str) -> List[ProductInfo]:
		pass 

	def _extract_product_details(self, product_url: str) -> ProductInfo:
		try:
			logger.info(f"Extracting details from: {product_url}")

			req = Request(
				product_url, 
				headers={"User-Agent": web_config["http"]["user_agent"]}
			)
			html = urlopen(req)
			bs = BeautifulSoup(html, "html.parser")

			detail_selectors = self.scraping_config["product_detail_selectors"]
			name_element = bs.select_one(detail_selectors["name"])
			product_name = name_element.text.strip() if name_element else ""
   
			description_element = bs.select_one(detail_selectors["description"])
			product_description = description_element.text.strip() if description_element else ""
			
			# price_element = bs.select_one(detail_selectors.get("unit_price", "")).text.strip()
			# match = re.search(r"([\d.,]+)\s*([a-zA-ZđĐ]+)", price_element)
			# if match:
			# 	product_unit_price = match.group(1)
			# 	product_currency = match.group(2)
			# else:
			# 	product_unit_price = 0 
			# 	product_currency = ""

			product_uprice = bs.select_one(detail_selectors.get("unit_price", "")).text.strip()
			product_currency = bs.select_one(detail_selectors.get("currency", "")).text.strip() 
   
			image_element = bs.select_one(detail_selectors.get("image_selector", ""))
			images = []
			if image_element:
				imgs_container = image_element.select('.swiper-slide')
				for img in imgs_container:
					src = img.find('img').get('src')
					if src:
						images.append(src)
      
			categories = []
			categories_element = bs.select_one(detail_selectors.get("original_category", ""))
			if categories_element:
				tags = categories_element.find_all("a", rel="tag")
				for tag in tags:
					tag_name = tag.get_text(strip=True)
					if tag:
						categories.append(tag_name)
							
			product = ProductInfo(
				product_name=product_name,
				product_url=product_url,
				original_category=categories,
				website_name=self.website_name,
				product_code="",
				product_description=product_description,
				product_unit_price=product_uprice,
				product_currency=product_currency,
				product_image=images
			)

			return product 
		except Exception as e:
			logger.error(f"Error extracting product details from {product_url}")
			logger.error(str(e))
			return None 
		

	
		