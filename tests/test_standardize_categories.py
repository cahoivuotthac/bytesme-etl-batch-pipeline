import pandas as pd 
from ops.transform.standardize_categories import standardize_category
from utils.logger_config import setup_logger

logger = setup_logger()

df = pd.read_csv('data/staging/bingsu_products.csv')
df_transform = df.copy()

print(f"Total rows in input: {len(df)}")


mapped_categories = standardize_category(df[['product_name', 'original_category']])
print(f"Total mapped categories: {len(mapped_categories)}")
print(f"Unique transformed cats: {set(mapped_categories)}")

df_transform['category_name'] = mapped_categories
df_transform.drop('original_category', axis=1, inplace=True)
logger.info(f"5 first categories in transformed dataset: {df_transform['category_name'].head()}")

df_transform.to_csv('data/staging/bingsu_products.csv', index=False)
	