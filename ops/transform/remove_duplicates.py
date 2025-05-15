import logging
import pandas as pd

logger = logging.getLogger(__name__)

def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
	key_cols = ['product_name', 'product_url']
	df_unique = df.drop_duplicates(subset=key_cols, keep='first')
	
	logger.info(f"Removed {len(df) - len(df_unique)} duplicate records")
	
	return df_unique

# if __name__ == '__main__':
# 	df = pd.read_csv('data/raw/bingsu_products.csv')
# 	df = remove_duplicates(df)
# 	df.to_csv('data/staging/bingsu_products.csv')