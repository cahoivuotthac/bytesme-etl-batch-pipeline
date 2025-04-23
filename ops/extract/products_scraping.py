from dataclasses import dataclass, field
import re
import time
from typing import Dict, List
from urllib.parse import urljoin
from urllib.request import Request, urlopen
from bs4 import BeautifulSoup
import requests
from utils.logging_config import setup_logging, load_config

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service 
from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException
from webdriver_manager.chrome import ChromeDriverManager

import time 

logger = setup_logging()
web_config = load_config("webs_config.yml")
SCROLL_PAUSE_TIME = 2

@dataclass 
class ProductInfo:
    
	# metadata 
	product_name: str
	product_url: str
	website_name: str 
	original_category: List[str] = field(default_factory=list)
 
	product_image: List[str] = field(default_factory=list)
	product_image_type: int = 1 
	product_image_name: str = ""
 
	product_code: str = "" # sku 
	product_description: str = ""
	product_unit_price: int = 0
	product_currency: str="VND"
	product_discount_percentage: float = 0.0
	product_total_orders: int = 10
	product_stock_quantity: int = 50
	product_total_ratings: int = 0
	product_overall_stars: float = 0.0

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
			all_products = self._crawl_pagination(current_page, isSingle=False)
		elif loading_type == "single-page":
			all_products = self._crawl_pagination(current_page, isSingle=True)	
		elif loading_type == "progressive":
			all_products = self._crawl_progessive(current_page)
		
		logger.info(f"Products count: {len(all_products) if all_products else 0}")
		return all_products
	
	def _crawl_pagination(self, url: str, isSingle: bool) -> List[ProductInfo]:
		products = []
		next_selector = self.scraping_config["pagination"]["next_selector"]
		
		logger.info("Start pagination crawling ...")
		logger.debug(f"Next selector: {next_selector}")
		
		while url: 
			try:
				headers = {
					'User-Agent': web_config["http"]["user_agent"],
					'Connection': 'keep-alive'
				}
				html = requests.get(url, headers=headers)
				bs = BeautifulSoup(html.content, "html5lib")
    
				products_info = self._crawl_each_page(bs)
				products.extend(products_info)

				if isSingle == False:
					next_page = bs.select_one(next_selector)
					url = next_page.get('href') if next_page else None 
				else:
					return products 
 
			except Exception as e:
				logger.error(f"Error occured when extracting products")
				
		return products

	def _crawl_progessive(self, url: str) -> List[ProductInfo]:
		options = Options()
		options.add_argument('--headless') # run without opening a browser 
		driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

		try:
			logger.info(f"Starting progressive scroll extraction from: {url}")
			driver.get(url)
			
			while True:
				try: 
					load_more_button = driver.find_element(By.CLASS_NAME, self.scraping_config["progressive_loading"]["button_selector"])
					load_more_button.click()
					time.sleep(SCROLL_PAUSE_TIME)
     
				except NoSuchElementException:
					logger.info("No more loadmore button founded")
					break 
 
				except ElementClickInterceptedException:
					logger.info("Button is not clickable right now ...")
					time.sleep(SCROLL_PAUSE_TIME)

			html = driver.page_source
			bs = BeautifulSoup(html, "html5lib")
			products_info = self._crawl_each_page(bs)
			return products_info

		except Exception as e:
			logger.error(f"Error during progressive scrolling: {str(e)}")
			return []

		finally:
			driver.quit()
			
	def _crawl_each_page(self, bs: BeautifulSoup) -> List[ProductInfo]:
		products= []

		product_tag = self.scraping_config["product_tag"]
		product_selector = self.scraping_config["product_selector"]
		product_cards = bs.find_all(
	   		product_tag, 
	      	class_=re.compile(product_selector.replace(".", ""))
	    )

		for card in product_cards:
			product_url = card.get('href')
			logger.debug(f"Product url: {product_url}")

			# make url absolute if it's relative 
			if not product_url.startswith('https://'):
				website_path = self.website_config["path"]["website_path"]
				website_path = website_path.rstrip('/')
				product_url = urljoin(website_path, product_url)

			# get detailed product info 
			product = self._extract_product_details(product_url)
			if product: 
				products.append(product)

		return products 

	def _extract_product_details(self, product_url: str) -> ProductInfo:
		try:
			logger.info(f"Extracting details from: {product_url}")

			headers = {
				'User-Agent': web_config["http"]["user_agent"]
			}
			html = requests.get(product_url, headers=headers)
			bs = BeautifulSoup(html.text, "html.parser")
			detail_selectors = self.scraping_config.get("product_detail_selectors", "")
   
			name_elem = bs.select_one(detail_selectors.get("name", ""))
			if name_elem:
				product_name = name_elem.text.strip() if name_elem else ""
			if detail_selectors["description"] != "None":
				description_elem = bs.select_one(detail_selectors.get("description", ""))
				product_description = description_elem.text.strip()
			else: 
				product_description = ""

			price_elem = bs.select_one(detail_selectors.get("unit_price", ""))
			logger.debug(f"Raw price element: {price_elem}")
			if price_elem:
				try:
					price_text = price_elem.get_text(strip=True)
					product_uprice = int(''.join(filter(str.isdigit, price_text)))
					logger.debug(f"Unit price: {product_uprice}")
 
					currency_selector = price_elem.find('span')
					product_currency = currency_selector.get_text(strip=True) if currency_selector else "₫"
					logger.debug(f"Currency: {product_currency}")
     
				except Exception as e: 
					logger.error(f"Error parsing price: str{e}")
     
			image_elem = bs.select_one(detail_selectors.get("image_selector", ""))
			images = []
			if image_elem:
				imgs_container = image_elem.select('.swiper-slide')
				for img in imgs_container:
					src = img.find('img').get('src')
					if src:
						images.append(src)
      
			categories = []
			categories_elem = bs.select_one(detail_selectors.get("original_category", ""))
			if categories_elem:
				tags = categories_elem.find_all("a", rel="tag")
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
