import pandas as pd
from utils.logging_config import setup_logging

logger = setup_logging()

def remove_duplicates(input_path: str, output_path: str):
	df = pd.read_csv(input_path)
	
	unique_df = df.drop_duplicates()
	
	unique_df.to_csv(output_path, index=False)
	
	logger.info(f"Removed {len(df) - len(unique_df)} duplicate records")
	
	