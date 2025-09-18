import logging
import os
from pathlib import Path
import json

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

def setup_logger(log_name: str):
	base_dir = Path(__file__).parent.parent 
	log_dir = os.path.join(base_dir, "logs")
	os.makedirs(log_dir, exist_ok=True)
 
	logging.basicConfig(
		filename=os.path.join(log_dir, log_name),
		level=logging.DEBUG,
		format='%(asctime)s - %(levelname)s - %(message)s'
	)
	
	return logging.getLogger()

def load_webconfig(config_path: str):
	base_dir = Path(__file__).parent 
	with open(os.path.join(base_dir, config_path), 'r') as f: 
		data = json.load(f) 
	return data 

def setup_selenium(user_agent: str) -> ChromeDriverManager:
	options = Options()
  
	options.add_argument('--headless')
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
  
		