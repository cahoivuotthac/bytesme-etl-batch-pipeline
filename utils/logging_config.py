import logging
import os

import yaml

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

def setup_logging(log_name='scraping.log'):
	log_folder="logs"
	os.makedirs(log_folder, exist_ok=True)
 
	logging.basicConfig(
		filename=os.path.join(log_folder, log_name),
		level=logging.DEBUG,
		format='%(asctime)s - %(levelname)s - %(message)s'
	)
	
	return logging.getLogger()

def load_config(path):
	base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
	config_path = os.path.join(base_dir, "utils", path)
	
	with open(config_path, 'r') as f: 
		config = yaml.safe_load(f)
	
	return config

def setup_selenium(user_agent: str) -> ChromeDriverManager:
	options = Options()
  
	# options.add_argument('--headless')
	options.add_argument('--no-sandbox')
	options.add_argument('--disable-dev-shm-usage')
	options.add_argument('--disable-blink-features=AutomationControlled')
	options.add_argument(f'--user-agent={user_agent}')
	options.add_experimental_option("excludeSwitches", ["enable-automation"])
	options.add_experimental_option('useAutomationExtension', False)
	
	driver = webdriver.Chrome(
		service=Service(ChromeDriverManager().install()),
		options=options
	)

	driver.execute_script("""
		(function(open) {
			XMLHttpRequest.prototype.open = function() {
				open.apply(this, arguments);
				this.setRequestHeader('User-Agent', arguments[1].indexOf('localhost') > -1 ? '' : 'Mozilla/5.0');
				this.setRequestHeader('Accept', '*/*');
			};
		})(XMLHttpRequest.prototype.open);
	""")
 
	return driver