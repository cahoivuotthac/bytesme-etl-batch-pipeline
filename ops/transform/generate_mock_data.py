import os
import time
import pandas as pd
from config.logger_config import setup_logger
import numpy as np 
import requests
from dotenv import load_dotenv

load_dotenv()

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

def generate_product_description_with_ollama(row):
	# First install Ollama: https://ollama.com/
	# Then run: ollama pull <model_name>
	
	"""
	The extract process:
	- Internally thinking in English 
	- Generating the description content in English 
	- Transalating that description to Vietnamese 
	"""
	
	try:
		
		input_prompt = f"""
            Write a detailed product description ONLY in Vietnamese for this beverage:
            Product name: {row['product_name']}
            Category: {row['category_name']}
            Price: {row['product_unit_price']} VND
            Rating: {row['product_overall_stars']}/5 ({row['product_total_ratings']} reviews)
            Units sold: {row['product_total_orders']} orders
            
            IMPORTANT RULES:
            - Write ONLY in Vietnamese language
            - Do NOT include the product information listed above
            - The description must be engaging, clear, and SEO-friendly
            - No special characters
        """
        
		response = requests.post('http://localhost:11434/api/generate', 
							   json={
								   'model': 'llama3',
								   'prompt': input_prompt,
								   'stream': False,
           							'temperature': 0.9
							   })
		
		result = response.json()
		
		return result['response']
	except Exception as e:
		print(f"Error generating description for {row['product_name']} with Ollama: {e}")
		return ""
		
def update_product_dataset(input_file: str, output_file: str) -> pd.DataFrame: 
	df = pd.read_csv(input_file)
	cat_counters = {}
	print("Checkpoint")
	if 'product_code' in df.columns:
		df['product_code'] = df['product_code'].astype(str)
	df_test = df[:5]
	for idx in range(len(df_test)):
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
  
		description = generate_product_description_with_ollama(df.loc[idx])
		df.at[idx, 'product_description'] = str(description) if description is not None else ''
		print(df.at[idx, 'product_description'])
  
	df['product_discount_percentage'] = generate_discount_percentage(len(df))

	os.makedirs('data/processed', exist_ok=True)
	output_file_exists = os.path.isfile(output_file)
 
	df.to_csv(
		output_file,
		index=False,
		mode='a' if output_file_exists else 'w',
		header=not output_file_exists
	)
	
	return df
 
# if __name__ == "__main__":
# 	input_file = 'data/processed/drink_products.csv'
# 	output_file = 'data/processed/drink_products_with_mock.csv'
# 	df = update_product_dataset(input_file, output_file)
# 	print(f"Total processed rows: {len(df)}")
# 	print("Finish")