import logging
import os

def setup_logging(log_name='scrapper.log'):
	log_folder="web_etl_pipeline/logs"
	os.makedirs(log_folder, exist_ok=True)
 
	logging.basicConfig(
		filename=os.path.join(log_folder, log_name),
		level=logging.INFO, 
		format='%(asctime)s - %(levelname)s - %(message)s'
	)
	
	return logging.getLogger()