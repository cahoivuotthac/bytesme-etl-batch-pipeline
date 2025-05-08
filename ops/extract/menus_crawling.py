import re
from urllib.error import HTTPError
from urllib.parse import urljoin, urlparse
from urllib.request import urlopen, Request
from bs4 import BeautifulSoup
from utils.logging_config import setup_logging, load_config

logger = setup_logging()
config = load_config("webs_config.yml")

def is_parent_category(url_list, url):
	parsed_url = urlparse(url)
 
	for u in url_list:
		parsed_u = urlparse(u)
    
		if urlparse(url).path != parsed_u.path and parsed_u.path.startswith(parsed_url.path):
			return True 

	return False 

def scrape_website(link, tag_name, menu_selector, filter_keyword):
	all_urls = set() # prevent duplicated urls 
	user_agent = config["http"]["user_agent"]
	
	try: 
		req = Request(
			link, 
			headers={
				'User-Agent': user_agent,
			}
		)
		html = urlopen(req)
		bs = BeautifulSoup(html, 'html.parser')
	 
		menu_list = bs.find_all(tag_name, attrs={"class": re.compile(menu_selector)})
		logger.debug(f"Menu list: {menu_list}")
		for menu in menu_list: 
			menu_items = menu.find_all('a', href=True)
   
			for item in menu_items:
				url = item['href']
				if url.startswith('#'):
					url = item['data-url']
     
				logger.debug(f"Url: {url}")
    
				if (filter_keyword == "None" or filter_keyword in url):
					# ensure absolute url 
					if not url.startswith('https://'):
						url = urljoin(link, url)

					all_urls.add(url) 
		
		all_list = list(all_urls)
		filtered_list = [url for url in all_list if not is_parent_category(all_list, url)]
    
		return filtered_list 

	except HTTPError as e:
		logger.error(f"HTTP Error:", {e.code})
		if e.code == 403: 
			logger.warning("Access forbidden")
	
	return list(all_urls) 

