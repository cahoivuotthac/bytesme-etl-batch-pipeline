from dataclasses import dataclass, field
from typing import Dict, List
from utils.logging_config import setup_logging

logger = setup_logging()

@dataclass 
class ProductInfo: 
	product_name: str
	product_url: str 
	original_category: str # process it later using NLP model 
	website_name: str 
 
	# db schema fields 
	product_code: str = "" # sku 
	product_description: str = ""
	product_unit_price: int = 0
	product_discount_percentage: float = 0.0
	product_total_orders: int = 10
	product_stock_quantity: int = 50
	product_total_ratings: int = 0
	product_overall_stars: float = 0.0
	product_image: List[str] = field(default_factory=list)
	product_image_type: int = 1 
	product_image_name: str = ""
 
class ProductExtractor: 
	""" 
 	Extract products from category pages 
	supporting both pagination and progressive loading 
  	"""

	def __init(self, website_config: Dict, website_name: str):
		self.website_config = website_config 
		self.website_name = website_name
		self.scraping_config = website_config.get('scraping', {})
		self.user_agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36"
	
	def extract_products(self, category_url: str, category_name: str) -> List[ProductInfo]:
		logger.info(f"Extracting products from {category_name} ({category_url})")
	
		all_products = []
		current_page = category_url

