import pandas as pd
from config.logger_config import setup_logger

logger = setup_logger()

def remove_duplicates(input_path: str, output_path: str):
	df = pd.read_csv(input_path)
	
	unique_df = df.drop_duplicates()
	
	unique_df.to_csv(output_path, index=False)
	
	logger.info(f"Removed {len(df) - len(unique_df)} duplicate records")
	
# remove_duplicates('data/raw/drink_products.csv', 'data/processed/drink_products.csv')	