import os
import pandas as pd
import yaml
from web_etl_pipeline.ops.parsing.menus_crawling import scrape_website
from web_etl_pipeline.utils.logging_config import setup_logging

results = {}
logger = setup_logging()

def test_menu_parsing():
	config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                              'utils', 'parse_config.yml') # utls/parse_config.yml
	with open(config_path, 'r') as file:
		config = yaml.safe_load(file)
	
	website_config = config.get('websites', {})
	
	for site_name, site_config in website_config.items():
		try: 
			logger.info(f"Testing menu parsing for {site_name}")
			
			website_path = site_config['path']['website_path']
			tag_name = site_config['scraping']['tag_name']
			menu_selector = site_config['scraping']['menu_selector']
			filter_keyword = site_config['scraping']['filter-keyword']

			menu_urls = scrape_website(website_path, tag_name, menu_selector, filter_keyword)
   
			results[site_name] = {
				'success': True,
				'url_count': len(menu_urls),
				'sample_urls': menu_urls[:5] if menu_urls else []
			}
   
			save_path = site_config['path']['save_path']
			os.makedirs(save_path, exist_ok=True)
   
			df = pd.DataFrame(data=menu_urls, columns=["URL"])
			df.to_csv(
       			f"{save_path}/{site_name}_urls.csv",
          		index=site_config['dataframe']['index'],
				header=site_config['dataframe']['header'],
				encoding=site_config['dataframe']['encoding']
			)
   
		except Exception as e: 
			logger.error(f"Error parsing {site_name}: {str(e)}")
			results[site_name] = {
				'success': False,
				'error': str(e)
			}

	return results 

if __name__ == "__main__":
	print("Testing menu parsing ...")
	results = test_menu_parsing()
	
	for site, rs in results.items():
		print("Site name:", site)
		if rs['success'] == True:
			print(f"Success! Found {rs['url_count']} links")
			print("Sample links: ")
			for url in rs['sample_urls']:
				print(f" - {url}")
		else: 
			print(f"Failed: {rs['error']}")
   
	print("\nDetailed logs available in the logs directory")
