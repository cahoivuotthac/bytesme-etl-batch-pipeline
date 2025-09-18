import re
import requests 

from urllib.error import HTTPError
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from utils.helpers import setup_logger

logger = setup_logger("menus_crawling.log")
config = setup_logger.load_config("webs_config.yml")

def is_parent_category(url_list, parent_url):
	for u in url_list:
		parsed_u = urlparse(u)
    
		if urlparse(parent_url).path == parsed_u.path:
			return False 

	return True 

def scrape_website(link, tag_name, menu_selector, filter_keyword):
	all_product_urls = set() 
	user_agent = config["user_agent"]
	
	try: 
		html = requests.get(
			link, 
			headers={
				'User-Agent': user_agent,
			}
		)
		if html.status_code == 200:
			bs = BeautifulSoup(html.content, 'html5lib')
	 
		menu_list = bs.find_all(tag_name, attrs={"class": re.compile(menu_selector)})
		logger.debug(f"Menu list: {len(menu_list)}")
		for menu in menu_list: 
			menu_items = menu.find_all('a', href=True)
   
			for item in menu_items:
				url = item['href']
				if url.startswith('#'):
					url = item['data-url']
     
				logger.debug(f"Url: {url}")
    
				if filter_keyword == "None" or filter_keyword in url:
					if not url.startswith('https://'):
						url = urljoin(link, url)

					all_product_urls.add(url) 
		
		all_list = list(all_product_urls)
		unique_list = [url for url in all_list if not is_parent_category(all_list, url)]
    
		return unique_list 

	except HTTPError as e:
		logger.error(f"HTTP Error:", {e.code})
		if e.code == 403: 
			logger.warning("Access forbidden")


