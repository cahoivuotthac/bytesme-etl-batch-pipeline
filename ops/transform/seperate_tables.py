import csv
import datetime
import glob
import logging
import os


logger = logging.getLogger(__name__)
categories = {} 
products = []
product_images_names = []

# categories_info = {
# 	''
# }

def _process_input_file(input_file: str):
	with open(input_file, encoding='UTF-8') as f:
		reader = csv.DictReader(f)
		
		for row in reader:
			category_name = row['category_name']
			category_type = 1 if category_name in ['Coffee', 'Tea', 'Chocolate & Cacao', 'Frosty'] else 0
			categories[category_name] = {
				'category_name': category_name,
				'category_background_url': '', 
                'category_type': category_type,
                'category_description': '',  
                'created_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'updated_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
			}

			product = {
				'product_code': row['product_code'],
                'product_name': row['product_name'],
                'product_description': row['product_description'],
                'product_band': row['product_brand'],
                'product_discount_percentage': float(row['product_discount_percentage']),
                'product_unit_price': row['product_unit_price'],  
                'product_total_orders': int(row['product_total_orders']),
                'product_total_ratings': int(row['product_total_ratings']),
                'product_overall_stars': float(row['product_overall_stars']),
                'product_stock_quantity': int(row['product_stock_quantity']),
                'category_name': row['category_name'], 
                'created_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'updated_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
			}
			products.append(product)
			
			if '|' in row['product_image']:
				images = [row['product_image'].split('|')]
				image_names = [row['product_name'].split('|')]
				for i, n in images, image_names:
					image_name = {
						'product_code': row['product_code'],
						'product_image': i,
						'product_image_name': n,
						'created_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                		'updated_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
					}
					product_images_names.append(image_name)
     
			else: 
				image_name = {
					'product_code': row['product_code'],
					'product_image': row['product_image'],
					'product_image_name': row.get('product_image_name', 'product_name'),
					'product_image_type': row.get('product_image_type', 1),
					'created_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                	'updated_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
				}
				product_images_names.append(image_name)
    
def _write_outputs(output_dir: str):
	os.makedirs(output_dir, exist_ok=True)

	category_id_map = {}
	for i, name in enumerate(categories.keys(), 1):
		category_id_map[name] = i
		# categories = {
		#     "Pastries": {"category_id": 1},
		# }
		categories[name]['category_id'] = i
  
	categories_file = os.path.join(output_dir, 'categories.csv')
	with open(categories_file, 'w', newline='', encoding='utf-8') as f:
		writer = csv.DictWriter(f, fieldnames=['category_id', 'category_name', 
											 'category_background_url', 'category_type', 
											 'category_description', 'created_at', 'updated_at'])

		writer.writeheader()
		for cat in categories.values():
			writer.writerow(cat)
   
	products_file = os.path.join(output_dir, 'products.csv')
	product_id_map = {}
	with open(products_file, 'w', newline='', encoding='UTF-8') as f:
		writer = csv.DictWriter(f, fieldnames=['product_id', 'category_id', 'product_code', 
											 'product_name', 'product_description', 'product_band',
											 'product_discount_percentage', 'product_unit_price',
											 'product_total_orders', 'product_total_ratings',
											 'product_overall_stars', 'product_stock_quantity',
											 'created_at', 'updated_at'])
		writer.writeheader()
		
		for i, product in enumerate(products, 1):
			category_name = product.pop('category_name') 
			category_id = category_id_map[category_name]

			product_id_map[product['product_code']] = i
   
			writer.writerow({
                'product_id': i,
                'category_id': category_id,
				**product # unpacking usage 
			})

	product_images_file = os.path.join(output_dir, 'product_images.csv')
	with open(product_images_file, 'w', newline='', encoding='UTF-8') as f:
		writer = csv.DictWriter(f, fieldnames=['product_image_id', 'product_id', 
												'product_image', 'product_image_name',
												'product_image_type', 'create_at', 'update_at'])
  
		for i, product in enumerate(product_images_names, 1):
			product_code = product_images_names.pop('product_code')
			product_id = product_id_map[product_code]

			writer.writerow({
				'product_image_id': i,
				'product_id': product_id,
				**product 	
			})
   
	logger.info(f"Separated data into {len(categories)} categories, {len(products)} products, and {len(product_images_names)} product images")
	logger.info(f"Output files saved to {output_dir}")
 
	return {
		'categories': categories_file,
		'products': products_file,
		'product_images': product_images_file,
		'status': 'success'
	} 

def seperate_tables(input_dir: str, output_dir: str):
	csv_files = glob.glob(os.path.join(input_dir, '*_products.csv'))
	for file in csv_files:
		_process_input_file(file)
	
	return _write_outputs(output_dir)