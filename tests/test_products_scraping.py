import json
import os 
import pandas as pd
from ops.extract.products_scraping import ProductExtractor
from config.logger_config import load_config
from config.logger_config import setup_logger

logger = setup_logger()
config = load_config("webs_config.yml")

web_config = config["websites"]
web_names = web_config.keys()

with open("data/bingsu_urls.json") as f:
    category_urls = json.load(f)

all_products = []
for name in web_names:
    for url in category_urls[name]:
        extractor = ProductExtractor(web_config, name, url)
        products = extractor.process_pages()
        if products:    
            all_products.extend(products)

flat_products = []
for product in all_products:
    product_dict = {}
    for key, value in product.__dict__.items():
        if isinstance(value, list):
            product_dict[key] = '|'.join(str(item) for item in value)
        else:
            product_dict[key] = value 
   
    flat_products.append(product_dict)
        
df = pd.DataFrame(data=flat_products)

# Create dir if not exist 
os.makedirs('data/raw', exist_ok=True)

file_path = 'data/raw/bingsu_products.csv' 
file_exist = os.path.isfile(file_path)

df.to_csv(
    file_path,
    index=False, 
    mode='a' if file_exist else 'w',    
    header=not file_exist, 
    encoding='utf-8')

logger.info(f"Saved {len(df)} products to CSV in tabular format")       