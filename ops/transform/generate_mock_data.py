import json
import logging
import os
import time
import pandas as pd
import numpy as np 
import requests

logger = logging.getLogger(__name__)

def _generate_product_code(product_brand: str, product_cat: str, iter: int) -> str:
	brand = product_brand[:2].upper()
	cat = product_cat[:2].upper()
 
	product_code = f"{brand}-{cat}-{str(iter + 1).zfill(3)}"
	return product_code
                       
def _generate_discount_percentage(num_products: int) -> int:
	discount_prob = 0.3
	has_discount = np.random.rand(num_products) < discount_prob
	
	return np.where(
		has_discount, 
		np.random.randint(5, 50, size=num_products),
		0
	)   

def _generate_total_ratings() -> int: 
    # most products have relatively few ratings, but some popular ones have many
    # using a power-law-like distribution
	return int(np.random.exponential(scale=50)) + 1 

def _generate_overall_stars() -> float:
    # using beta distribution skewed toward higher values (most products 3.5+ stars)
	return round(np.random.beta(4, 1.5) * 4 + 1, 1)

DEFAULT_BASE_PRICE = 50000

def _generate_total_orders() -> int: 
    return np.random.randint(0, 500)

def _generate_product_description_with_ollama(row):
	# First install Ollama: https://ollama.com/
	# Then run: ollama pull <model_name> 

	try:
		
		input_prompt = f"""
			Viết mô tả ngắn gọn về sản phẩm topping ăn kèm với các món ngọt khác có tên {row['product_name']}  
			
		"""
		response = requests.post('http://localhost:11434/api/generate', 
							   json={
								   'model': 'mrjacktung/phogpt-4b-chat-gguf',
								   'prompt': input_prompt,
								   'stream': False,
           							# 'temperature': 0.8 # level of creativity 
							   })
		
		result = response.json()
		
		return result['response']
	except Exception as e:
		print(f"Error generating description for {row['product_name']} with Ollama: {e}")
		return ""

def _generate_json_size_price(base_price: int, cate_name: str) -> json:
	sizes = ['S', 'M', 'L']
 
	additional_price = 5000
	if cate_name == 'Cakes':
		additional_price = 12000
  
	prices = [base_price + i * additional_price for i in range(len(sizes))]
 
	return {
		'product_sizes': '|'.join(sizes),
		'product_prices': '|'.join(str(price) for price in prices) 
	}

def update_product_dataset(df: pd.DataFrame, output_file: str) -> pd.DataFrame: 
	cat_counters = {}
	print("Checkpoint")
	if 'product_code' in df.columns:
		df['product_code'] = df['product_code'].astype(str)

	df['product_overall_stars'] = df['product_overall_stars'].astype(float)
	df['product_unit_price'] = df['product_unit_price'].astype(object)
 
	for idx in range(len(df)):
		web_name = df.at[idx, 'product_brand']
		cat_name = df.at[idx, 'category_name']
		
		if cat_name not in cat_counters:
			cat_counters[cat_name] = 0
   
		df.at[idx, 'product_code'] = _generate_product_code(
			product_brand=web_name,
			product_cat=cat_name,
			iter=cat_counters[cat_name]
		)

		cat_counters[cat_name] += 1

		df.at[idx, 'product_total_ratings'] = _generate_total_ratings()
  
		df.at[idx, 'product_overall_stars'] = _generate_overall_stars()
		df.at[idx, 'product_total_orders'] = _generate_total_orders()

		processed_cols = ['Bingsu', 'Frosty', 'Tea', 'Chocolate & Cacao', 'Coffee',
                    'Chilled & Cold', 'Cakes']
		
		cur_price = int(df.at[idx, 'product_unit_price'])
		if cur_price == 0:
			cur_price = DEFAULT_BASE_PRICE
			logger.debug(f"Check current price: {cur_price}")
   
		cur_cate = df.at[idx, 'category_name'] 
  
		if cur_cate in processed_cols:
			df.at[idx, 'product_unit_price'] = _generate_json_size_price(cur_price, str(cur_cate))
			logger.info(f"Check product price: {df.at[idx, 'product_unit_price']}")
		else: 
			if cur_price == 0:
				logger.info("Checkpoint")
				mock_price = np.random.randint(low = 55000, high=200000) 
				df.at[idx, 'product_unit_price'] = {'product_price': str(mock_price)}
				logger.info(f"Check product price: {df.at[idx, 'product_unit_price']}")	
    
		# if pd.isna(df.at[idx, 'product_description']) or df.at[idx, 'product_description'] == '':
		# 	description = _generate_product_description_with_ollama(df.loc[idx])
		# 	df.at[idx, 'product_description'] = str(description) if description is not None else ''
		# 	logger.info(f"Check product description: {description}") 
    
	df['product_discount_percentage'] = _generate_discount_percentage(len(df))

	os.makedirs('data/staging', exist_ok=True)
	output_file_exists = os.path.isfile(output_file)
	# df = df.drop(columns=['Unnamed'])
	df.to_csv(
		output_file,
		index=False,
		mode='w',
		# header=not output_file_exists
	)	
	
	return df

df = pd.read_csv('data/staging/topping_products.csv')
df_new = update_product_dataset(df, "data/staging/topping_products.csv")
