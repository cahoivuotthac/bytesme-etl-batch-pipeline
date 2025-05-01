import json

import pandas as pd
from ops.extract.products_scraping import ProductExtractor
from utils.logging_config import load_config
from utils.logging_config import setup_logging

logger = setup_logging()
config = load_config("webs_config.yml")

web_config = config["websites"]
web_names = web_config.keys()

with open("data/test/category_urls.json") as f:
    category_urls = json.load(f)

all_products = []
for name in web_names:
    extractor = ProductExtractor(web_config, name)
    for url in category_urls[name]:
        products = extractor.process_pages(url)
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
df.to_csv('data/test/cake_products.csv', index=False, encoding='utf-8')
logger.info(f"Saved {len(df)} products to CSV in tabular format") 