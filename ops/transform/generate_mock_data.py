import os
import time
import pandas as pd
from utils.logging_config import setup_logging
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
	# Then run: ollama pull tinyllama
	
	"""
	The extract process:
	- Taking Vietnamese prompt 
	- Internally thinking in English 
	- Generating the description content in English 
	- Transalating that description to Vietnamese 
	"""
	
	try:
		
		input_prompt = f"""
			Hãy viết một đoạn mô tả sản phẩm chi tiết bằng tiếng Việt cho một loại đồ uống, dựa trên các thông tin sau:
			- Tên sản phẩm: {row['product_name']}
			- Danh mục: {row['category_name']}
			- Giá bán: {row['product_unit_price']} VND
			- Đánh giá: {row['product_overall_stars']}/5 ({row['product_total_ratings']} lượt đánh giá)
			- Số lượng đã bán: {row['product_total_orders']} đơn
			Mô tả cần hấp dẫn, rõ ràng và chuẩn SEO để đăng trên website bán hàng. Mô tả không bao gồm các thông tin mô tả được chỉ ra ở phía trên.
			Phần mô tả không được chứa các kí tự đặc biệt. 
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
  
		description = generate_product_description_with_ollama(df.loc[idx])
		df.at[idx, 'product_description'] = str(description) if description is not None else ''
		print(f"Product description: {df.at[idx, 'product_description']}")
  
	df['product_discount_percentage'] = generate_discount_percentage(len(df))

	os.makedirs('data/processed', exist_ok=True)
	output_file_exists = os.path.isfile(output_file)
 
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