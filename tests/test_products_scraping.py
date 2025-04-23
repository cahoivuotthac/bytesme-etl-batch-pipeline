import json

import pandas as pd
from ops.extract.products_scraping import ProductExtractor
from utils.logging_config import load_config
from utils.logging_config import setup_logging

logger = setup_logging()
config = load_config("webs_config.yml")

web_config = config["websites"]
web_names = web_config.keys()

for name in web_names:
    extractor = ProductExtractor(web_config, name)

    with open("data/test/category_urls.json") as f:
        category_urls = json.load(f)

    # Collect all products in a flat list
    all_products = [] 
    for url in category_urls[name]:
        products = extractor.process_pages(url)
        if products:
            # Handle case where process_pages returns either a list or a single product
            if isinstance(products, list):
                all_products.extend(products)
            else:
                all_products.append(products)

    # Convert product objects to flat dictionaries
    flat_products = []
    for product in all_products:
        product_dict = {}
        
        # Extract attributes from product object
        if hasattr(product, '__dict__'):
            for key, value in product.__dict__.items():
                # Handle lists (like product_image) by joining with commas
                if isinstance(value, list):
                    product_dict[key] = '|'.join(str(item) for item in value)
                else:
                    product_dict[key] = value
        else:
            # If it's already a dictionary
            product_dict = product
        
        flat_products.append(product_dict)

# Create DataFrame from the flattened dictionaries
df = pd.DataFrame(data=flat_products)

# Save to CSV with proper tabular format
df.to_csv('data/test/cake_products.csv', index=False, encoding='utf-8')
logger.info(f"Saved {len(df)} products to CSV in tabular format")