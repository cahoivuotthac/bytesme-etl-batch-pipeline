import glob
import json
import os
import uuid
import pandas as pd
from dotenv import load_dotenv
import psycopg2
from langchain_postgres import PGVector
from langchain_core.documents import Document
from config.logger_config import setup_logger
from langchain_huggingface import HuggingFaceEmbeddings
from psycopg2.extensions import register_adapter, AsIs

load_dotenv()
logger = setup_logger('embeddings_transform.log')

def adapt_uuid(uuid_value):
    return AsIs(f"'{uuid_value}'")

register_adapter(uuid.UUID, adapt_uuid)

DB_HOST = os.getenv("POSTGRES_HOST")
DB_PORT = os.getenv("POSTGRES_DB_PORT")
DB_NAME = os.getenv("POSTGRES_DB_NAME")
DB_USER = os.getenv("POSTGRES_DB_USER")
DB_PASSWORD = os.getenv("POSTGRES_DB_PASSWORD")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SCHEMA_NAME = "analytics"

# Configure connection string for PGVector
CONNECTION_STRING = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?options=-c%20search_path%3D{SCHEMA_NAME}%2Cpublic"
COLLECTION_NAME = "product_pg_embeddings"

def _create_text_for_embedding(product_data):
    text_parts = []
    
    name_parts = []
    if 'product_name' in product_data and pd.notna(product_data['product_name']):
        name_parts.append(f"Sản phẩm có tên gọi {product_data['product_name']}.")
    
    if 'product_brand' in product_data and pd.notna(product_data['product_brand']):
        name_parts.append(f"Thương hiệu của sản phẩm {product_data['product_brand']}.")
    
    if 'category_name' in product_data and pd.notna(product_data['category_name']):
        name_parts.append(f"Sản phẩm thuộc về danh mục phân loại {product_data['category_name']}.")
    
    if name_parts:
        text_parts.append(" ".join(name_parts))
    
    if 'product_description' in product_data and pd.notna(product_data['product_description']) and str(product_data['product_description']).strip():
        desc = str(product_data['product_description']).strip()
        if len(desc) > 1000:
            desc = desc[:1000] + "..."
        text_parts.append(f"Mô tả sản phẩm: {desc}")
    
    price_section = []
    if 'product_unit_price' in product_data and pd.notna(product_data['product_unit_price']):
        price_info = product_data['product_unit_price']
        currency = product_data.get('product_currency', '') if pd.notna(product_data.get('product_currency', '')) else ''
        
        if isinstance(price_info, str) and price_info.startswith('{'):
            try:
                price_dict = json.loads(price_info.replace("'", '"'))
                if 'product_sizes' in price_dict and 'product_prices' in price_dict:
                    sizes = price_dict['product_sizes'].split('|')
                    prices = price_dict['product_prices'].split('|')
                    
                    price_text = "Sản phẩm có nhiều size với nhiều mức giá khác nhau: "
                    price_text += ", ".join([f"{size} for {currency}{price}" for size, price in zip(sizes, prices)])
                    price_section.append(price_text)
            except:
                price_section.append(f"Giá bán của sản phẩm {price_info} {currency}.")
        else:
            price_section.append(f"Giá bán của sản phẩm {price_info} {currency}.")
    
    if 'product_discount_percentage' in product_data and pd.notna(product_data['product_discount_percentage']):
        try:
            discount = float(product_data['product_discount_percentage'])
            if discount > 0:
                price_section.append(f"Sản phẩm đang được giảm giá {discount}% phần trăm.")
        except (ValueError, TypeError):
            pass
    
    if price_section:
        text_parts.append(" ".join(price_section))
    
    popularity_section = []
    if 'product_overall_stars' in product_data and pd.notna(product_data['product_overall_stars']):
        try:
            stars = float(product_data['product_overall_stars'])
            if stars > 4.5:
                popularity_section.append(f"Sản phẩm này được đánh giá rất cao với {stars} sao trên 5.")
            elif stars > 3.5:
                popularity_section.append(f"Sản phẩm này được đánh giá tốt với {stars} sao trên 5.")
            else:
                popularity_section.append(f"Sản phẩm này có số điểm đánh giá là {stars} sao trên 5.")
        except (ValueError, TypeError):
            pass

    if 'product_total_ratings' in product_data and pd.notna(product_data['product_total_ratings']):
        try:
            ratings = int(product_data['product_total_ratings'])
            popularity_section.append(f"Sản phẩm đã được {ratings} khách hàng đánh giá.")
        except (ValueError, TypeError):
            pass

    if 'product_total_orders' in product_data and pd.notna(product_data['product_total_orders']):
        try:
            orders = int(product_data['product_total_orders'])
            if orders > 1000:
                popularity_section.append(f"Đây là sản phẩm bán chạy với hơn {orders} lượt đặt hàng.")
            else:
                popularity_section.append(f"Sản phẩm đã được đặt hàng {orders} lần.")
        except (ValueError, TypeError):
            pass

    if popularity_section:
        text_parts.append(" ".join(popularity_section))
    
    if 'product_stock_quantity' in product_data and pd.notna(product_data['product_stock_quantity']):
        try:
            stock = int(product_data['product_stock_quantity'])
            if stock > 100:
                text_parts.append("Sản phẩm này còn nhiều hàng và sẵn sàng để giao.")
            elif stock > 20:
                text_parts.append("Sản phẩm này hiện đang có sẵn trong kho.")
            elif stock > 0:
                text_parts.append("Sản phẩm này chỉ còn lại một số lượng ít.")
            else:
                text_parts.append("Sản phẩm này hiện đang hết hàng.")
        except (ValueError, TypeError):
            pass
 
    if 'category_name' in product_data and pd.notna(product_data['category_name']):
        category = product_data['category_name'].lower()
        
    if any(term in category for term in ['cookie', 'biscuit']):
        text_parts.append("Bánh quy giòn rụm, trẻ em có thể rất yêu thích.")

    if any(term in category for term in ['cake']):
        text_parts.append("Đây là món tráng miệng mềm ngọt, thường được thưởng thức sau bữa ăn hoặc ăn vặt trong các buổi xế chiều.")

    if any(term in category for term in ['bingsu', 'chilled', 'cold', 'frosty']):
        text_parts.append("Đây là món ăn hoặc thức uống mát lạnh, sảng khoái, thích hợp dùng trong thời tiết nóng bức.")

    if any(term in category for term in ['pastry', 'pie']):
        text_parts.append("Đây là loại bánh được nướng thơm lừng, vỏ giòn rụm, thường làm từ bột mì và có vị ngọt hoặc mặn.")

    if any(term in category for term in ['drink', 'tea', 'coffee', 'chocolate', 'cacao', 'frosty']):
        text_parts.append("Đây là một loại đồ uống thơm ngon, thích hợp để giải khát.")

    if 'coffee' in category:
        text_parts.append("Đây là đồ uống cà phê đậm đà, giúp tỉnh táo và khơi dậy năng lượng.")

    if 'tea' in category:
        text_parts.append("Trà thanh mát, thơm đậm, có thể dùng nóng hoặc lạnh tùy theo sở thích. Đồng thời trà cũng giúp tỉnh táo.")

    if any(term in category for term in ['chocolate', 'cacao']):
        text_parts.append("Đây là đồ uống từ sô cô la hoặc ca cao, hơi đắng nhẹ, béo ngậy, ngọt ngào và hấp dẫn.")

    if any(term in category for term in ['season', 'specialist']):
        text_parts.append("Đây là món bánh theo mùa, chỉ có trong thời gian giới hạn.")

    if 'set' in category:
        text_parts.append("Đây là một bộ sản phẩm gồm nhiều món tráng miệng. Có thể dùng làm quà tặng bạn bè, nguời thân vào các dịp đặc biệt")

    if any(term in category for term in ['topping', 'thêm']):
        text_parts.append("Đây là topping thêm, dùng để kết hợp với món chính nhằm tăng hương vị.")

    return " ".join(text_parts)

def _create_metadata_dict(product_data):
    return {
		'product_code': product_data.get('product_code', ''),
        'product_name': product_data.get('product_name', ''),
        'category_name': product_data.get('category_name', '')
	}
    
def load_all_product_data(input_dir):
    all_products = []
    
    csv_files = glob.glob(os.path.join(input_dir, '*_products.csv'))
    
    if not csv_files:
        logger.warning(f"No product CSV files found in {input_dir}")
        return all_products
    
    for file_path in csv_files:
        file_name = os.path.basename(file_path)
        logger.info(f"Processing {file_name}")
        
        try:
            df = pd.read_csv(file_path)
            products = df.to_dict(orient='records')
            all_products.extend(products)
            
        except Exception as e:
            logger.error(f"Error loading {file_name}: {e}")

    return all_products

def prepare_documents(products):
    """Convert product data to LangChain Document objects for embedding"""
    
    documents = []
    
    for product in products:
        text = _create_text_for_embedding(product)
        
        metadata = _create_metadata_dict(product)
        
        # Crate Document object 
        doc = Document(
			page_content=text,
			metadata=metadata
		)
        
        documents.append(doc)
        
    logger.info(f"Preparing {len(documents)} for embedding")
    return documents

def create_embeddings_and_store(documents):
    """Create embeddings and store them directly in the database."""
    embeddings_model = HuggingFaceEmbeddings(
        model_name="intfloat/e5-base-v2",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True}
    )
 
    # Process in batches to avoid memory issues 
    batch_size = 50
    total_batches = (len(documents) + batch_size - 1) // batch_size
    
    try:
        # Set up database connection
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        
        cursor = conn.cursor()
        # Create schema
        cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA_NAME};")
        cursor.execute(f"SET search_path TO {SCHEMA_NAME}, public;")
        
        try:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        except Exception as e:
            logger.warning(f"Could not create vector extension (may need admin rights): {e}")
        
        # Drop existing tables to start fresh
        cursor.execute("DROP TABLE IF EXISTS langchain_pg_embedding;")
        cursor.execute("DROP TABLE IF EXISTS langchain_pg_collection;")
        
        # Create collection table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS langchain_pg_collection (
            id UUID PRIMARY KEY,
            name TEXT NOT NULL,
            cmetadata JSONB
        );
        """)
        
        # Create embedding table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS langchain_pg_embedding (
            id UUID PRIMARY KEY,
            collection_id UUID REFERENCES langchain_pg_collection(id),
            embedding VECTOR(768),
            document TEXT,
            cmetadata JSONB
        );
        """)
        
        # Create collection entry
        collection_id = uuid.uuid4()
        cursor.execute("""
        INSERT INTO langchain_pg_collection (id, name, cmetadata)
        VALUES (%s, %s, %s);
        """, (collection_id, COLLECTION_NAME, json.dumps({})))
        
        # Process documents in batches
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i+batch_size]
            batch_num = i // batch_size + 1
            
            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} documents)")
            
            # Process each document in the batch
            for doc in batch:
                # Generate embedding
                embedding_vector = embeddings_model.embed_query(doc.page_content)
                
                # Insert into database
                cursor.execute("""
                INSERT INTO langchain_pg_embedding (id, collection_id, embedding, document, cmetadata)
                VALUES (%s, %s, %s::vector, %s, %s);
                """, (
                    uuid.uuid4(),
                    collection_id,
                    embedding_vector,
                    doc.page_content,
                    json.dumps(doc.metadata)
                ))
            
            # Commit after each batch
            conn.commit()
            
        cursor.close()
        conn.close()
        
        logger.info(f"Successfully stored {len(documents)} documents with embeddings")
        return True
    except Exception as e:
        logger.error(f"Error creating embeddings: {e}")
        raise
    
def get_full_product_details(product_codes):
    """Retrieve full product details from app_data after vector search for testing"""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        
        cursor = conn.cursor()
        
        # Convert list to tuple for SQL IN clause
        if len(product_codes) == 1:
            codes_tuple = f"('{product_codes[0]}')"
        else:
            codes_tuple = tuple(product_codes)
        
        query = """
        SELECT 
            p.product_id,
            p.product_code,
            p.product_name,
            c.category_name,
            p.product_description,
            p.product_unit_price,
            p.product_discount_percentage,
            p.product_overall_stars
        FROM 
            app_data.products p
        JOIN 
            app_data.categories c ON p.category_id = c.category_id
        WHERE
            p.product_code IN %s
        """
        
        cursor.execute(query, (codes_tuple,))
        
        # Convert results to list of dictionaries
        columns = [desc[0] for desc in cursor.description]
        results = []
        
        for row in cursor.fetchall():
            results.append(dict(zip(columns, row)))
        
        cursor.close()
        conn.close()
        
        return results
    except Exception as e:
        logger.error(f"Error retrieving product details: {e}")
        return []
    
def test_search(query, top_k=3):
    """Test search functionality using vector distance with proper casting."""
    try:
        embeddings_model = HuggingFaceEmbeddings(
            model_name="intfloat/e5-base-v2",
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True}
        )
        
        # Generate embedding vector for the query
        query_embedding = embeddings_model.embed_query(query)
        
        # Connect to database
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        
        cursor = conn.cursor()
        cursor.execute(f"SET search_path TO {SCHEMA_NAME}, public;")
        
        # Convert the embedding array to a vector using the pgvector syntax
        cursor.execute("""
        SELECT 
            e.document,
            e.cmetadata,
            e.embedding <-> %s::vector AS distance
        FROM 
            langchain_pg_collection c
        JOIN 
            langchain_pg_embedding e ON c.id = e.collection_id
        WHERE 
            c.name = %s
        ORDER BY 
            distance ASC
        LIMIT %s
        """, (query_embedding, COLLECTION_NAME, top_k))
        
        results = []
        for row in cursor.fetchall():
            document_text, metadata_json, distance = row
            
            # Fix: Check the type of metadata_json before trying to parse it
            if isinstance(metadata_json, dict):
                metadata = metadata_json  # Already a dict, no need to parse
            elif metadata_json:
                # It's a string, parse it
                metadata = json.loads(metadata_json)
            else:
                metadata = {}
                
            document = Document(page_content=document_text, metadata=metadata)
            results.append((document, float(distance)))
        
        cursor.close()
        conn.close()
        
        # Extract product codes from the results
        product_codes = []
        for doc, _ in results:
            if 'product_code' in doc.metadata:
                product_codes.append(doc.metadata['product_code'])
        
        # Get full product details
        product_details = get_full_product_details(product_codes)
        
        # Print results for testing
        print("\nSearch Results for:", query)
        print("=" * 50)
        
        for i, ((doc, distance), product) in enumerate(zip(results, product_details)):
            if product:
                print(f"Result {i+1}:")
                print(f"Product: {product['product_name']}")
                print(f"Category: {product['category_name']}")
                print(f"Price: ${product['product_unit_price']}")
                print(f"Similarity Score: {1 - distance:.4f}")
                print("-" * 50)
        
        return results, product_details
    except Exception as e:
        logger.error(f"Error testing search: {e}")
        return [], []
    
def main(input_dir, run_test_search=True):
    try:
        products = load_all_product_data(input_dir)
        if not products:
            logger.error("No products found to process")
            return 
        
        documents = prepare_documents(products)
        success = create_embeddings_and_store(documents)
        if success and run_test_search:
            test_search("Món tráng miệng mềm mịn ngọt ngào", 3)
            test_search("Thức uống mát lạnh giúp tỉnh táo", 3)
            test_search("Món tráng miệng cho mùa hè nóng bức", 3)
          
    except Exception as e:
        logger.error(f"Error in main function: {e}")
        return
    
if __name__ == "__main__":
	main('data/staging')
    
	print("Done")