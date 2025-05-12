from dataclasses import dataclass, field
import json
import re
import time
from typing import Dict, List
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import requests
from config.logger_config import setup_logger, load_config, setup_selenium

from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import time 

logger = setup_logger()
web_config = load_config("webs_config.yml")
driver = setup_selenium(web_config["http"]["user_agent"])

import logging
logging.getLogger('selenium').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)

SCROLL_PAUSE_TIME = 3
SLEEP_TIME = 5
@dataclass 
class ProductInfo:
	
	# metadata 
	product_name: str
	product_url: str
	product_band: str 
 
	category_name: List[str] = field(default_factory=list)
	product_image: List[str] = field(default_factory=list)
	product_image_type: int = 1 
	product_image_name: str = ""
 
	product_code: str = "" # sku 
	product_description: str = ""
	product_unit_price: int = 0
	product_currency: str="₫"
	product_discount_percentage: float = 0.0
	product_total_orders: int = 0
	product_stock_quantity: int = 50
	product_total_ratings: int = 0
	product_overall_stars: float = 0.0

class ProductExtractor: 
	""" 
 	Extract products for both pagination and progressive loading techniques
  	"""

	def __init__(self, websites_config: Dict, website_name: str, category_url: str):
		# instance attributes
		self.website_config = websites_config.get(website_name, {}) 
		self.website_name = website_name
		self.scraping_config = self.website_config.get('scraping', {})
		self.popups_handled = False 
		self.category_url = category_url

	def process_pages(self) -> List[ProductInfo]:
		logger.info(f"Extracting products from: ({self.category_url})")
	
		all_products = []
		current_page = self.category_url # first page 

		loading_type = self.scraping_config['loading_type']
		if loading_type == "pagination":
			all_products = self._crawl_pagination(current_page)
		elif loading_type == "single-page":
			all_products = self._crawl_single_page(current_page)	 
		elif loading_type == "progressive":
			all_products = self._crawl_progessive(current_page)
		elif loading_type == "tab-based":
			all_products = self._crawl_tab_based(current_page)
   
		logger.info(f"Products count: {len(all_products) if all_products else 0}")
		time.sleep(5)
  
		return all_products

	def _crawl_single_page(self, product_url:str) -> List[ProductInfo]:
		logger.info(f"Starting single page extraction from: {product_url}")
	
		try:
			headers = {
				'User-Agent': web_config["http"]["user_agent"],
				'Connection': 'keep-alive'
			}
			html = requests.get(product_url, headers=headers)
			bs = BeautifulSoup(html.content, "html5lib")
			
			# Extract all products from the single page
			products = self._crawl_each_page(bs)
			
			if not products:
				logger.warning("No products found on the single page")
				return []
				
			logger.info(f"Successfully extracted {len(products)} products from single page")
			return products

		except Exception as e:
			logger.error(f"Error occurred when extracting products from single page: {str(e)}")
			return []
    
	def _hanlde_popups(self):
		if not self.popups_handled:
		# cookies popup 
			try:
				WebDriverWait(driver, 10).until(
				    EC.presence_of_element_located((By.ID, "CybotCookiebotDialog"))
				)
				allow_all_button = driver.find_element(By.ID, "CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll")
				allow_all_button.click()
				WebDriverWait(driver, 5).until(
				    EC.invisibility_of_element_located((By.ID, "CybotCookiebotDialog"))
				)
			except Exception as e:
				logger.warning(f"Cookies popup not found or failed to close: {str(e)}")

			try: 
				close_button = WebDriverWait(driver, 10).until(
					EC.element_to_be_clickable((By.CSS_SELECTOR, "div[class^='storefront-sdk-emotion'] button"))
				)
				close_button.click()
			except Exception as e:
				logger.warning(f"Close button not found or failed to click: {str(e)}")

			self.popups_handled = True 

	def _add_products(self, products: List[ProductInfo], processed_urls: set) -> List[ProductInfo]:
		products_info = []
		
		for product in products:
			if product.product_url not in processed_urls: 
				products_info.append(product)
				processed_urls.add(product.product_url)	

		return products_info

	def _crawl_tab_based(self, url: str) -> List[ProductInfo]:
		try:
			driver.get(url)
			logger.info(f"Loading page: {url}")
			time.sleep(3)
			self._hanlde_popups()

			products_info = []
			processed_url = set()
   
			logger.info("Waiting for tabs to be loaded ...")
			try: 
				tabs = WebDriverWait(driver, 15).until(
				    EC.presence_of_all_elements_located((By.CSS_SELECTOR, self.scraping_config["subcategory_selector"]))
				)
				logger.debug(f"Found {len(tabs)} tabs")
	   
				# extract products from the initial page 
				html = driver.page_source 
				bs = BeautifulSoup(html, 'html5lib')
				initial_products = self._crawl_each_page(bs)
				if initial_products:
					products_info.extend(self._add_products(initial_products, processed_url))
    
				for i in range(1, len(tabs)): 
					try: 
					
						driver.execute_script("arguments[0].click();", tabs[i])
						WebDriverWait(driver, 15).until(
						    EC.presence_of_all_elements_located((By.CSS_SELECTOR, self.scraping_config["product_selector"]))
						)

						html = driver.page_source
						bs = BeautifulSoup(html, 'html5lib')
						products = self._crawl_each_page(bs)
						if products:
							products_info.extend(self._add_products(products, processed_url))

					except ElementClickInterceptedException:
						logger.warning("Element click intercepted. Retrying...")
						time.sleep(5)

						driver.execute_script("arguments[0].click();", tabs[i])
						products = WebDriverWait(driver, 15).until(
						    EC.presence_of_all_elements_located((By.CSS_SELECTOR, self.scraping_config["product_selector"]))
						)
						
						if products: 
							html = driver.page_source
							bs = BeautifulSoup(html, 'html5lib')
							products_info.extend(self._add_products(products, processed_url))
						else: 
							continue
		      
			except TimeoutException: 
				logger.warning("No tabs are founded within the timeout period")
    
				html = driver.page_source
				bs = BeautifulSoup(html, 'html5lib')
				products = self._crawl_each_page(bs)
				if products:
					products_info.extend(self._add_products(products, processed_url))
    
			return products_info
 
		except Exception as e:
			error_message = str(e) if str(e) else repr(e) # repr: developer-oriented representation
			error_type = type(e).__name__ 
			logger.error(f"WebDriver error: {error_type} - {error_message}")

			logger.debug("Current URL: " + url)
			return []
		
	def _crawl_pagination(self, url: str) -> List[ProductInfo]:
		products = []
		processed_urls = set()
  
		page_count = 0
		max_pages = 20
  
		next_selector = self.scraping_config["pagination"]["next_selector"]
		logger.debug(f"Next selector: {next_selector}")
		
		logger.info("Start pagination crawling ...")
		
		while url and page_count < max_pages: 
			page_count += 1
			try:
				headers = {
					'User-Agent': web_config["http"]["user_agent"],
					'Connection': 'keep-alive'
				}
				html = requests.get(url, headers=headers)
				bs = BeautifulSoup(html.content, "html5lib")
				products_info = self._crawl_each_page(bs)
				
				for product in products_info:
					if product.product_url not in processed_urls:
						processed_urls.add(product.product_url)
						products.append(product)

				next_page = bs.select_one(next_selector)
				if next_page: 
					url = next_page.get('href')
				else: 
					continue
			
			except Exception as e:
				logger.error(f"Error occured when extracting products: str({e})")
				
		return products

	def _crawl_progessive(self, url: str) -> List[ProductInfo]:
		try:
			logger.info(f"Starting progressive extraction from: {url}")
			driver.get(url)
			
			# wait for the page to be fully loaded 
			time.sleep(SLEEP_TIME)

			products_info = []
			max_attemps = 5
			attempt_count = 0
   
			while attempt_count < max_attemps:
				try: 
					# Try scrolling to make button visible
					driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
					time.sleep(SLEEP_TIME)
	 
					# button selector is a CSS selector including both a class and an element
					load_more_button = driver.find_element(By.CSS_SELECTOR, self.scraping_config["button_selector"])
					
					while load_more_button and load_more_button.is_displayed():
						logger.debug(f"Load More button found: {load_more_button}")
						
						driver.execute_script("arguments[0].scrollIntoView(true);", load_more_button)
						logger.debug("Clicked the Load More button.")
		 
						driver.execute_script("arguments[0].click();", load_more_button)
						time.sleep(SCROLL_PAUSE_TIME)
						load_more_button = driver.find_element(By.CSS_SELECTOR, self.scraping_config["button_selector"])

					break 
						
				except NoSuchElementException:
					logger.info("No more loadmore button founded")
					break 

				except ElementClickInterceptedException:
					logger.info("Button is not clickable right now ...")
					attempt_count += 1
					if attempt_count == max_attemps:
						break 
					time.sleep(SCROLL_PAUSE_TIME)
					continue 
 
			logger.info("Out of the loop")
			html = driver.page_source
			bs = BeautifulSoup(html, 'html5lib')
			current_products = self._crawl_each_page(bs)
			logger.debug(f"Extracted {len(current_products)} products from the current page.")
			if not current_products:
				logger.warning("No products found on the current page.")

			products_info.extend(current_products)
     
		except Exception as e:
			logger.error(f"WebDriver error: {str(e)}")
			return []

		finally: 
			if driver in locals():
				driver.quit()
    
		return products_info

	def _crawl_each_page(self, bs: BeautifulSoup) -> List[ProductInfo]: 
		products= []

		product_tag = self.scraping_config["product_tag"]
		product_selector = self.scraping_config["product_selector"]
		product_cards = bs.find_all(
	   		product_tag, 
		  	class_=re.compile(product_selector.replace(".", ""))
		)
		
		logger.info(f"Found {len(product_cards)} product elements")

		skip_products = 0
		for card in product_cards:
			logger.debug(f"Product card: {card}")
			product_url = card.get('href')
			if not product_url:
				anchor = card.find('a')
				if anchor:
					product_url = anchor.get('href')
			
			if product_url:
				skip_patterns = self.scraping_config["skip_url_patterns"] 
				if skip_patterns != "None" and skip_patterns in product_url:
					continue  
 
			logger.debug(f"Product url: {product_url}")

			# make url absolute if it's relative 
			if product_url and not product_url.startswith('https://'):
				website_path = self.website_config["path"]["website_path"]
				website_path = website_path.rstrip('/')
				product_url = urljoin(website_path, product_url)
				logger.debug(f"Transformed product url: {product_url}")
			elif not product_url:
				logger.warning("Found a product card with no url")
				skip_products += 1
				continue 

			# get detailed product info 
			product = self._extract_product_details(product_url)
			if product: 
				products.append(product)

		logger.warning(f"Skip {skip_products} products")
		return products 

	def _extract_product_details(self, product_url: str) -> ProductInfo:
		try:
			logger.info(f"Extracting details from: {product_url}")

			headers = {
				'User-Agent': web_config["http"]["user_agent"]
			}
			html = requests.get(product_url, headers=headers)
			bs = BeautifulSoup(html.content, "html5lib")
			detail_selectors = self.scraping_config.get("product_detail_selectors", "")

			# logger.debug("Product detail page HTML content:")
			# logger.debug(bs.prettify())
			
			product_info = self._extract_from_html(bs, detail_selectors, product_url)
			logger.debug(f"Product info check: {product_info}")
   
			# extract product info from meta tags
			if not product_info.product_name and not product_info.product_unit_price:
				logger.info("HTML extraction failed or incomplete, attempting meta extraction...")
				product_info = self._extract_from_meta(bs, product_url)

			return product_info

		except Exception as e:
			logger.error(f"Error extracting product details from {product_url}")
			logger.error(str(e))
			return None 

	def _extract_from_html(self, bs, detail_selectors, product_url) -> ProductInfo:
		logger.info("Extract from HTML")

		product_name = ""
		product_description = ""
		product_uprice = 0  # Initialize price to 0
		images = []
		image_names = []
		categories = []
  
		# name
		name_elem = bs.select_one(detail_selectors["name"])
		
		if name_elem != "None":
			product_name = name_elem.text.strip() if name_elem else ""

		logger.debug(f"Product name: {product_name}")
  
		if detail_selectors["description"] != "None":
			product_description = ""
			description_selectors = detail_selectors["description"]
			
			# Check if description_selectors is a string or a list
			if isinstance(description_selectors, str):
				# Handle single selector as string
				description_elem = bs.select_one(description_selectors)
				if description_elem:
					product_description = description_elem.text.strip()
			else:
				# Handle multiple selectors as list
				for selector in description_selectors:
					description_elem = bs.select_one(selector)
					if description_elem:
						product_description = description_elem.text.strip()
						break 
		else: 
			product_description = ""

		logger.debug(f"Product description: {product_description}")
  
		# price, currency
		if detail_selectors["unit_price"] != "None":
			price_elem = bs.select_one(detail_selectors["unit_price"])

			logger.debug(f"Raw price element HTML: {price_elem}")
			if price_elem:
				try:
					price_text = price_elem.get_text(strip=True)
					logger.debug(f"Raw price text: {price_text}") 

					# remove currency symbols and commas 
					cleaned_price_text = re.sub(r'[^\d]', '', price_text)
					
					if cleaned_price_text.isdigit():
						product_uprice = int(cleaned_price_text)
						logger.debug(f"Unit price: {product_uprice}")
				except Exception as e:
					logger.error(f"Error parsing price: {str(e)}")
 
				except Exception as e: 
					logger.error(f"Error parsing price: str{e}")
			else: 
				product_uprice = 0

		# images
		images = []
		image_names = []
		imgs_con = bs.select_one(detail_selectors.get("image_selector", ""))
		logger.debug(f"Image HTML content: {imgs_con}")

		if imgs_con:
			if detail_selectors["detail_image"] != "None":
				imgs = imgs_con.select(detail_selectors["detail_image"])
				logger.debug(f'Image element: {imgs}')
				
				for img_div in imgs:
					try:
						img = img_div.find('img')
						if img:
							src = img.get('data-large_image') or img.get('src')
							name = None
							
							for attr in ['alt', 'title', 'data-caption']:
								if img.get(attr):
									name = img.get(attr)
									if name:
										# clean the title
										name = name.replace('_optimized', '')
										name = re.sub(r'\.[^.]+$', '', name)  # remove file extension
										break
							
							if not name:
								# extract name from src URL as fallback
								name = src.split('/')[-1].split('.')[0]
								name = name.replace('-', ' ').replace('_', ' ')
							
							if not src.startswith("https://"):
								src = 'https://' + src.lstrip('//')

							# logger.debug(f"Image source: {src}")
							# logger.debug(f"Image name: {name}")

							if src:
								images.append(src)
							if name:
								image_names.append(name)
				
					except Exception as e:
						logger.error(f"Error extracting image details: {str(e)}")
						continue

		# specific for the tljus website
			if 'style' in imgs_con.attrs:
				style_attr = imgs_con.attrs['style']
				match = re.search(r'url\(["\']?(.*?)["\']?\)', style_attr)
				if match:
					src = match.group(1)
					if not src.startswith("https://"):
						src = 'https://' + src
					logger.debug(f"Extracted image source from style: {src}")
					images.append(src)
					image_names.append("")
		else:
			logger.warning(f"No image container found")
    
		# categories
		categories = []
		category_selector = detail_selectors['original_category']
		if category_selector and category_selector != "None":
			if isinstance(category_selector, str) and category_selector.startswith("literal:"):
				category_value = category_selector[8:]
				categories.append(category_value)
			else:
       
				categories_elem = bs.select_one(category_selector)
				logger.debug(f"Category list: {categories_elem}")

				if categories_elem:
					tags = categories_elem.find_all(detail_selectors["category_tag"])
					for tag in tags:
						if not tag.__contains__('Sản phẩm nổi bật'):
							tag_name = tag.get_text(strip=True)
						
							categories.append(tag_name)
   
			if not categories: 
				parsed_url = urlparse(product_url) 
				path_parts = parsed_url.path.strip('/').split('/')
				categories.append(path_parts[-2])
    
		logger.debug(f"Categories: {categories}")

		# sku 
		code_elem = bs.select_one(detail_selectors["code"]) if detail_selectors["code"] else ""
		product_code = code_elem.get_text(strip=True) if code_elem else ""
		logger.debug(f"SKU: {product_code}")
  
		product = ProductInfo(
			product_name=product_name,
			product_url=product_url,
			category_name=categories,
			product_band=self.website_name,
			product_code=product_code,
			product_description=product_description,
			product_unit_price=product_uprice,
			product_image=images,
			product_image_name=image_names
		)

		return product

	# Schema.org markup 
	def _extract_from_meta(self, bs, product_url) -> ProductInfo:
		try:
			logger.info("Extract from meta")
			
			meta_name = bs.find('meta', {'property': 'og:title'})
			meta_price = bs.find('meta', {'property': 'og:price:amount'})
			meta_image = bs.find('meta', {'property': 'og:image'})
			
			if any([meta_name, meta_price, meta_image]):
				logger.debug("Found product data in meta tags")
				
				product_name = meta_name['content'] if meta_name else ''
				product_uprice = int(''.join(re.findall(r'\d', meta_price['content']))) if meta_price else 0
				product_image = [meta_image['content']] if meta_image else []
			
			# product description 
			scripts = bs.find_all('script')
			xr_data = None
			for script in scripts:
				if script.string and 'const xr =' in script.string:
					try:
						match = re.search(r'const xr =\s*(\[.*?\]);', script.string, re.DOTALL)
						if match:
							json_str = match.group(1)
							# Parse the JSON array
							product_data = json.loads(json_str)[0]  # Get first item
							if 'product_description' in product_data:
								product_description = product_data['product_description']
								logger.debug(f"Found product description: {product_description}")
								break
					except json.JSONDecodeError as e:
						logger.error(f"Error parsing product JSON: {str(e)}")
					except Exception as e:
						logger.error(f"Error extracting product description: {str(e)}")
      
			# product category 			
			parsed_url = urlparse(self.category_url)
			path_parts = parsed_url.path.strip('/').split('/')
			product_category = path_parts[-1] 
			
			product = ProductInfo(
				product_name=product_name,
				product_url=product_url,
				category_name=product_category,
				product_band=self.website_name,
				product_code="",
				# product_description=product_description,
				product_unit_price=product_uprice,
				product_image=product_image,
				product_image_name=[product_name.lower()] if product_name else []
			)
			
			logger.debug(f"Created product info: {product}")
			return product

		except Exception as e:
			logger.error(f"Error extracting from meta tags: {str(e)}")
			return None
      