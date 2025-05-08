import os
import pandas as pd
from utils.logging_config import setup_logging
import random 
import numpy as np 

def generate_product_code(website_name: str, product_cat: str, iter: int) -> str:
	brand = website_name[:2].upper()
	cat = product_cat[:2].upper()
 
	product_code = f"{brand}-{cat}-{str(iter + 1).zfill(3)}"
	
	return product_code
                       
def generate_discount_percentage(num_products: int) -> int:
	discount_prob = 0.3
	has_discount = np.random.rand(num_products) < discount_prob
	
	return np.where(
		has_discount, 
		np.random.randint(5, 50, size=num_products),
		0
	)   

def generate_total_ratings() -> int: 
    # most products have relatively few ratings, but some popular ones have many
    # using a power-law-like distribution
	return int(np.random.exponential(scale=50)) + 1 

def generate_overall_stars() -> float:
    # using beta distribution skewed toward higher values (most products 3.5+ stars)
	return round(np.random.beta(4, 1.5) * 4 + 1, 1)

def generate_total_orders() -> int: 
    return np.random.randint(0, 500)


def update_product_dataset(input_file: str, output_file: str) -> pd.DataFrame: 
	df = pd.read_csv(input_file)
	cat_counters = {}
	
	if 'product_code' in df.columns:
		df['product_code'] = df['product_code'].astype(str)
  
	for idx in range(len(df)):
		web_name = df.at[idx, 'website_name']
		cat_name = df.at[idx, 'category_name']
		
		if cat_name not in cat_counters:
			cat_counters[cat_name] = 0
   
		df.at[idx, 'product_code'] = generate_product_code(
			website_name=web_name,
			product_cat=cat_name,
			iter=cat_counters[cat_name]
		)

		cat_counters[cat_name] += 1

		df.at[idx, 'product_total_ratings'] = generate_total_ratings()
		df.at[idx, 'product_overall_stars'] = generate_overall_stars()
		df.at[idx, 'product_total_orders'] = generate_total_orders()
  

	df['product_discount_percentage'] = generate_discount_percentage(len(df))

	# os.makedirs('data/processed', exist_ok=True)
	# output_file_exists = os.path.isfile(output_file)
 
	df.to_csv(
		output_file,
		index=False,
		# mode='a' if output_file_exists else 'w',
		# header=not output_file_exists
	)
	
	return df
 
if __name__ == "__main__":
	input_file = 'data/processed/drink_products.csv'
	output_file = 'data/processed/drink_products_with_mock.csv'
	df = update_product_dataset(input_file, output_file)
	print(f"Total processed rows: {len(df)}")
	print("Finish")