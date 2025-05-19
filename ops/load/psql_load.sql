\copy app_data.categories FROM 'data/processed/categories.csv' DELIMITER ',' CSV HEADER;

\copy app_data.products FROM 'data/processed/products.csv' DELIMITER ',' CSV HEADER;

\copy app_data.product_images FROM 'data/processed/product_images.csv' DELIMITER ',' CSV HEADER;
