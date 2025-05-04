import pandas as pd 
from ops.transform.standardize_categories import standardize_category
from utils.logging_config import setup_logging

logger = setup_logging()

df = pd.read_csv('data/test/unique_cake_products.csv')
df_transform = df.copy()

# print(f"Unique categories in input: {df['original_category'].unique()}")
print(f"Total rows in input: {len(df)}")
# logger.info(f"5 first categories in initial dataset: {df['original_category'].head()}")

# new_standard_categories = standardize_category(df['original_category'].tolist())

mapped_categories = standardize_category(df[['product_name', 'original_category']])
print(f"Total mapped categories: {len(mapped_categories)}")
print(f"Unique transformed cats: {set(mapped_categories)}")

# for i in range(len(mapped_categories)):
#     print(f"Name: {df['product_name'][i]} - Raw Category: {df['original_category'][i]} - Category: {mapped_categories[i]}")
df_transform['category_name'] = mapped_categories
df_transform.drop('original_category', axis=1, inplace=True)
logger.info(f"5 first categories in transformed dataset: {df_transform['category_name'].head()}")

df_transform.to_csv('data/test/transformed_cake_products.csv', index=False)
