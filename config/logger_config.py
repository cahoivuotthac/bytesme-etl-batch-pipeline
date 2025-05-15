import logging
import os
import requests
import yaml

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv

load_dotenv()

def setup_logger(log_name='scraping.log'):
	log_folder="logs"
	os.makedirs(log_folder, exist_ok=True)
 
	logging.basicConfig(
		filename=os.path.join(log_folder, log_name),
		level=logging.DEBUG,
		format='%(asctime)s - %(levelname)s - %(message)s'
	)
	
	return logging.getLogger()

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


def setup_discord_notification(logger):
    webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
    
    if not webhook_url:
        logger.warning("No Discord webhook URL provided, notifications disabled")
        return
    
    class DiscordWebhookHandler(logging.Handler):
        def emit(self, record):
            # Only send ERROR and higher severity
            if record.levelno >= logging.ERROR:
                log_entry = self.format(record)
                payload = {
                    "content": f"⚠️ **ETL Pipeline Error**\n```\n{log_entry}\n```"  # Fixed formatting
                }
                
                try:
                    requests.post(webhook_url, json=payload)
                except Exception as e:
                    print(f"Failed to send Discord notification: {e}")
    
    discord_handler = DiscordWebhookHandler()
    discord_handler.setLevel(logging.ERROR)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    discord_handler.setFormatter(formatter)
    logger.addHandler(discord_handler)
  
		