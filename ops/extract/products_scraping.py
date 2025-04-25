from dataclasses import dataclass, field
import re
import time
from typing import Dict, List
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import requests
from utils.logging_config import setup_logging, load_config, setup_selenium

from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import time 

logger = setup_logging()
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
	website_name: str 
	original_category: List[str] = field(default_factory=list)
 
	product_image: List[str] = field(default_factory=list)
	product_image_type: int = 1 
	product_image_name: str = ""
 
	product_code: str = "" # sku 
	product_description: str = ""
	product_unit_price: int = 0
	product_currency: str="₫"
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
		self.popups_handled = False 

	def process_pages(self, category_url: str) -> List[ProductInfo]:
		logger.info(f"Extracting products from: ({category_url})")
	
		all_products = []
		current_page = category_url # first page 

		loading_type = self.scraping_config.get('loading_type', 'single-page')
		if loading_type == "pagination":
			all_products = self._crawl_pagination(current_page, isSingle=False)
		elif loading_type == "single-page":
			all_products = self._crawl_pagination(current_page, isSingle=True)	
		elif loading_type == "progressive":
			all_products = self._crawl_progessive(current_page)
		elif loading_type == "tab-based":
			all_products = self._crawl_tab_based(current_page)
   
		logger.info(f"Products count: {len(all_products) if all_products else 0}")
		time.sleep(5)
  
		return all_products

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

	def _crawl_tab_based(self, url: str) -> List[ProductInfo]:
		try:
			driver.get(url)
   
			self._hanlde_popups()
   
			logger.debug("Waiting for tabs to load...")
			tabs = WebDriverWait(driver, 15).until(
			    EC.presence_of_all_elements_located((By.CSS_SELECTOR, self.scraping_config["subcategory_selector"]))
			)
			logger.debug(f"Found {len(tabs)} tabs")
   
			products_info = []
			
			if tabs: 
				for tab in tabs: 
					try: 
						driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")	
      
						# Wait for the content to load
						html = driver.page_source
						bs = BeautifulSoup(html, 'html5lib')
						products = self._crawl_each_page(bs)
						products_info.extend(products)

						tab.click()
						logger.info("Tab menu is clicked")
      
					except ElementClickInterceptedException:
						logger.warning("Element click intercepted. Retrying...")
						time.sleep(1)
						driver.execute_script("arguments[0].click();", tab)
			else: 
				# If no tabs are found, scrape the current page
				logger.info("No tabs found. Scraping the current page.")
				html = driver.page_source
				bs = BeautifulSoup(html, 'html5lib')
				products = self._crawl_each_page(bs)
				products_info.extend(products)
			
			return products_info
 
		except Exception as e:
			logger.error(f"WebDriver error: {str(e)}")
			return []
		
		
	def _crawl_pagination(self, url: str, isSingle: bool) -> List[ProductInfo]:
		products = []
		if not isSingle:
			next_selector = self.scraping_config["pagination"]["next_selector"]
			logger.debug(f"Next selector: {next_selector}")
   
		logger.info("Start pagination crawling ...")
		
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

				if not isSingle:
					next_page = bs.select_one(next_selector)
					url = next_page.get('href') if next_page else None 
				else:
					return products 
 
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

		for card in product_cards:
			product_url = card.get('href')
			if not product_url:
				anchor = card.find('a')
				if anchor:
					product_url = anchor.get('href')
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
			bs = BeautifulSoup(html.content, "html5lib")
			detail_selectors = self.scraping_config.get("product_detail_selectors", "")

			# name
			name_elem = bs.select_one(detail_selectors["name"])
			if name_elem != "None":
				product_name = name_elem.text.strip() if name_elem else ""
			if detail_selectors["description"] != "None":
				description_elem = bs.select_one(detail_selectors.get("description", ""))
				product_description = description_elem.text.strip()
			else: 
				product_description = ""

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
			logger.debug(f"Image HTML conten: {imgs_con}")
   
			if imgs_con:
				if detail_selectors["detail_image"] != "None":
					imgs = imgs_con.select(detail_selectors["detail_image"])
				
					for img in imgs:
						logger.debug(f"{img.attrs}")
						
						img = img.find('img')
						
						src = img.get('src')
						name = img.get('alt') if img.get('alt') else ""
	  
						if not src.startswith("https://"):
							src = 'https://' + src
		  
						logger.debug(f"Image source: {src}")
						logger.debug(f"Image name: {name}")	
		 
						if src and name:
							images.append(src)
							image_names.append(name)
       
				# specific for the tljus website
				else:
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
   
			# categories
			categories = []
			if detail_selectors["original_category"] != "None":
				categories_elem = bs.select_one(detail_selectors["original_category"])
				if categories_elem:
					tags = categories_elem.find_all(detail_selectors["category_tag"])
					for tag in tags:
						tag_name = tag.get_text(strip=True)
						if tag:
							categories.append(tag_name)
			
			logger.debug(f"Categories: {categories}")

			# sku 
			code_elem = bs.select_one(detail_selectors["code"]) if detail_selectors["code"] else ""
			product_code = code_elem.get_text(strip=True) if code_elem else ""
			logger.debug(f"SKU: {product_code}")
   
			product = ProductInfo(
				product_name=product_name,
				product_url=product_url,
				original_category=categories,
				website_name=self.website_name,
				product_code=product_code,
				product_description=product_description,
				product_unit_price=product_uprice,
				product_image=images
			)

			return product 

		except Exception as e:
			logger.error(f"Error extracting product details from {product_url}")
			logger.error(str(e))
			return None 
