-- Full load reference database 
DROP DATABASE IF EXISTS bytesme_mobile;
CREATE DATABASE bytesme_mobile;
USE bytesme_mobile;

DROP TABLE IF EXISTS bytesme_mobile.products;
CREATE TABLE bytesme_mobile.products (
  product_id INT PRIMARY KEY AUTO_INCREMENT,
  category_name VARCHAR(50),
  sub_category_name VARCHAR(50),
  product_code VARCHAR(10),
  product_name VARCHAR(50) UNIQUE NOT NULL,
  product_description LONGTEXT,
  product_unit_price INT,
  product_discount_percentage FLOAT DEFAULT 0,
  product_total_orders INT,
  product_total_ratings INT,
  product_overall_stars FLOAT,
  product_stock_quantity INT DEFAULT 0,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);

DROP TABLE IF EXISTS bytesme_mobile.ingredients;
CREATE TABLE bytesme_mobile.ingredients (
  ingredient_id INT PRIMARY KEY AUTO_INCREMENT,
  ingredient_name VARCHAR(50) UNIQUE NOT NULL,
  ingredient_description TEXT,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);

DROP TABLE IF EXISTS bytesme_mobile.product_ingredients;
CREATE TABLE bytesme_mobile.product_ingredients (
  product_id INT,
  ingredient_id INT,
  amount_used VARCHAR(50),

  FOREIGN KEY (product_id) REFERENCES bytesme_mobile.products(product_id),
  FOREIGN KEY (ingredient_id) REFERENCES bytesme_mobile.ingredients(ingredient_id)
);

DROP TABLE IF EXISTS bytesme_mobile.product_images;
CREATE TABLE bytesme_mobile.product_images (
  product_image_id INT PRIMARY KEY AUTO_INCREMENT,
  product_id INT,
  product_image_name VARCHAR(100),
  product_image BLOB,
  product_image_url VARCHAR(255),
  image_type TINYINT(1),
  created_at TIMESTAMP,
  updated_at TIMESTAMP
  FOREIGN KEY (product_id) REFERENCES bytesme_mobile.products(product_id)
);
