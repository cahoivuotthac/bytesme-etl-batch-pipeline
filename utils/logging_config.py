import logging
import os

import yaml

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