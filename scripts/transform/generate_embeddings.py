import glob
import json
import os
import uuid
import pandas as pd
from dotenv import load_dotenv
import psycopg2
from langchain_core.documents import Document
from sentence_transformers import SentenceTransformer
from utils.logger_config import setup_logger
from psycopg2.extensions import register_adapter, AsIs
from sentence_transformers import SentenceTransformer
from pyvi.ViTokenizer import tokenize

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

VIETNAMESE_MODEL = "VoVanPhuc/sup-SimCSE-VietNamese-phobert-base"
EMBEDDING_DIMENSIONS = 768

def _create_text_for_embedding(product_data, category_map=None, category_descriptions=None):
    text_parts = []
    
    product_type = None
    drink_category_ids = [10, 11, 12, 13]  
    food_category_ids = [1, 2, 3, 4, 5, 6, 7, 8, 9]  
    
    if 'category_id' in product_data and pd.notna(product_data['category_id']):
        category_id = product_data['category_id']
        
        if category_id in drink_category_ids:
            product_type = "thức uống"
            text_parts.append("ĐÂY LÀ THỨC UỐNG. Đây là một loại đồ uống, không phải loại bánh ăn được. Sản phẩm này thuộc nhóm đồ uống giải khát.")
        elif category_id in food_category_ids:
            product_type = "món ăn"
            text_parts.append("ĐÂY LÀ MÓN ĂN hoặc BÁNH. Đây là đồ ăn, không phải đồ uống. Sản phẩm này thuộc nhóm thực phẩm ăn được.")
    
    category = ""
    category_desc = ""
    if 'category_id' in product_data and pd.notna(product_data['category_id']) and category_map is not None:
        category_id = product_data['category_id']
        if category_id in category_map:
            category = category_map[category_id].lower()
            text_parts.append(f"Sản phẩm thuộc danh mục {category_map[category_id]}.")
            
            if category_descriptions and category_id in category_descriptions:
                category_desc = category_descriptions[category_id]
                text_parts.append(f"Về danh mục này: {category_desc}")
    
    if product_type == "thức uống":
        if 'trà' in category.lower():
            text_parts.append("Đây là đồ uống trà thơm ngon, thích hợp giải khát. Trà là thức uống, không phải bánh. Đây là thức uống giúp tỉnh táo, thư giãn.")
        
        if 'cà phê' in category.lower():
            text_parts.append("Đây là đồ uống cà phê đậm đà. Cà phê là thức uống, không phải bánh. Đây là thức uống giúp tỉnh táo, tăng năng lượng.")
        
        if 'đá xay' in category.lower() or 'thức uống đá' in category.lower():
            text_parts.append("Đây là đồ uống đá xay mát lạnh, thích hợp giải nhiệt mùa hè. Đây là thức uống, không phải bánh.")
    
    elif product_type == "món ăn":
        if 'bánh ngọt' in category.lower() or 'bánh kem' in category.lower():
            text_parts.append("Đây là bánh ngọt mềm mịn, thơm phức. Bánh ngọt là đồ ăn, không phải đồ uống. Bánh ngọt có vị ngọt, mềm và không dùng để uống.")
        
        if 'bánh giòn' in category.lower() or 'bánh nướng' in category.lower() or 'bánh ngàn lớp' in category.lower():
            text_parts.append("Đây là bánh giòn, nướng vàng thơm phức. Bánh nướng là đồ ăn, không phải đồ uống. Bánh có độ giòn, vị mặn hoặc ngọt và không dùng để uống.")
        
        if 'bánh quy' in category.lower():
            text_parts.append("Đây là bánh quy giòn tan, thơm mùi bơ. Bánh quy là đồ ăn, không phải đồ uống. Bánh quy có độ giòn và không dùng để uống.")

    name_parts = []
    if 'product_name' in product_data and pd.notna(product_data['product_name']):
        product_name = product_data['product_name']
        name_parts.append(f"Sản phẩm có tên gọi {product_name}.")
        
        # Add product type reinforcement based on name keywords
        if product_type == "thức uống" or any(term in product_name.lower() for term in ['cà phê', 'coffee', 'trà', 'tea', 'đá xay', 'drink', 'nước']):
            name_parts.append("Đây là thức uống, không phải bánh ăn được.")
        elif product_type == "món ăn" or any(term in product_name.lower() for term in ['bánh', 'cake', 'pastry', 'cookie', 'bread']):
            name_parts.append("Đây là bánh ăn được, không phải thức uống.")
    
    if 'product_brand' in product_data and pd.notna(product_data['product_brand']):
        name_parts.append(f"Thương hiệu của sản phẩm {product_data['product_brand']}.")
    
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
                price_section.append(f"Sản phẩm đang được giảm giá {discount}%.")
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
                popularity_section.append(f"Sản phẩm này được đánh giá tốt với {stars} sao trên 3.5.")
            else:
                popularity_section.append(f"Sản phẩm này có số điểm đánh giá là {stars}.")
        except (ValueError, TypeError):
            pass

    if 'product_total_ratings' in product_data and pd.notna(product_data['product_total_ratings']):
        try:
            ratings = int(product_data['product_total_ratings'])
            popularity_section.append(f"Sản phẩm có tổng số lượt {ratings} khách hàng đánh giá.")
        except (ValueError, TypeError):
            pass

    if 'product_total_orders' in product_data and pd.notna(product_data['product_total_orders']):
        try:
            orders = int(product_data['product_total_orders'])
            if orders > 1000:
                popularity_section.append(f"Đây là sản phẩm bán chạy với hơn {orders} lượt đặt hàng.")
            else:
                popularity_section.append(f"Sản phẩm đã bán được {orders} đơn hàng.")
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
         
    if product_type == "thức uống":
        text_parts.append("Sản phẩm này là THỨC UỐNG. Dùng để giải khát, không phải để ăn. Đây là đồ UỐNG, không phải đồ ĂN.")
    elif product_type == "món ăn":
        text_parts.append("Sản phẩm này là BÁNH hoặc MÓN ĂN. Dùng để ăn, không phải để uống. Đây là đồ ĂN, không phải đồ UỐNG.")
    
    return " ".join(text_parts)

def _create_metadata_dict(product_data, category_map=None):
    metadata = {
        'product_code': product_data.get('product_code', ''),
        'product_name': product_data.get('product_name', '')
    }
    
    if category_map and 'category_id' in product_data and pd.notna(product_data['category_id']):
        category_id = product_data['category_id']
        if category_id in category_map:
            metadata['category_name'] = category_map[category_id]
    
    return metadata   
    
def load_all_product_data(input_file):
    all_products = []
    
    file_name = os.path.basename(input_file)
    logger.info(f"Processing {file_name}")
        
    try:
        df = pd.read_csv(input_file)
        products = df.to_dict(orient='records')
        all_products.extend(products)
        
    except Exception as e:
        logger.error(f"Error loading {file_name}: {e}")

    return all_products

def prepare_documents(products, category_map=None, category_descriptions=None):
    """Convert product data to LangChain Document objects for embedding"""
    
    documents = []
    
    for product in products:
        text = _create_text_for_embedding(product, category_map, category_descriptions)
        
        metadata = _create_metadata_dict(product, category_map)
        
        doc = Document(
			page_content=text,
			metadata=metadata
		)
        
        documents.append(doc)
        
    logger.info(f"Preparing {len(documents)} for embedding")
    return documents

_model = None 
def get_embedding_model():
    """
    Get or create a cached SentenceTransformer model optimized for Vietnamese.
    This prevents reloading the model multiple times during execution.
    """
    global _model
    if _model is None:
        try:
            logger.info(f"Load pretrained SentenceTransformer: {VIETNAMESE_MODEL}")
            _model = SentenceTransformer(VIETNAMESE_MODEL, device="cpu")
            logger.info(f"Successfully loaded model: {VIETNAMESE_MODEL}")
        except Exception as e:
            fallback_model = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
            logger.warning(f"Failed to load {VIETNAMESE_MODEL}, falling back to {fallback_model}: {e}")
            _model = SentenceTransformer(fallback_model, device="cpu")
    return _model

def embed_text(text):
    """Wrapper function to safely create embeddings"""
    try:
        model = get_embedding_model()
        embeddings = model.encode(text, normalize_embeddings=True)
        return embeddings.tolist()
    except Exception as e:
        logger.error(f"Error embedding text: {e}")
        # Return zeros array as fallback (with proper dimension)
        return [0.0] * EMBEDDING_DIMENSIONS

def create_embeddings_and_store(documents):
    """Create embeddings and store them directly in the database."""
    # Process in batches to avoid memory issues 
    batch_size = 50
    total_batches = (len(documents) + batch_size - 1) // batch_size
    
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT, 
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        
        cursor = conn.cursor()
        cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA_NAME};")
        cursor.execute(f"SET search_path TO {SCHEMA_NAME}, public;")
        
        try:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        except Exception as e:
            logger.warning(f"Could not create vector extension (may need admin rights): {e}")
        
        cursor.execute("DROP TABLE IF EXISTS langchain_pg_embedding;")
        cursor.execute("DROP TABLE IF EXISTS langchain_pg_collection;")
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS langchain_pg_collection (
            id UUID PRIMARY KEY,
            name TEXT NOT NULL,
            cmetadata JSONB
        );
        """)
        
        cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS langchain_pg_embedding (
            id UUID PRIMARY KEY,
            collection_id UUID REFERENCES langchain_pg_collection(id),
            embedding VECTOR({EMBEDDING_DIMENSIONS}),
            document TEXT,
            cmetadata JSONB
        );
        """)
        
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
                try:
                    # Generate embedding
                    embedding_vector = embed_text(doc.page_content)
                    
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
                except Exception as doc_error:
                    logger.error(f"Error processing document: {doc_error}")
                    continue
            
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
        query_embedding = embed_text(query)
        
        if all(v == 0.0 for v in query_embedding):
            logger.error("Query embedding failed, search results will be inaccurate")
         
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
            
            if isinstance(metadata_json, dict):
                metadata = metadata_json  
            elif metadata_json:
                metadata = json.loads(metadata_json)
            else:
                metadata = {}
                
            document = Document(page_content=document_text, metadata=metadata)
            results.append((document, float(distance)))
        
        cursor.close()
        conn.close()
        
        product_codes = []
        for doc, _ in results:
            if 'product_code' in doc.metadata:
                product_codes.append(doc.metadata['product_code'])
        
        product_details = get_full_product_details(product_codes)
        
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
    
def main(input_file, run_test_search=True):
    try:
        
        # mapping the category_name and category_id 
        categories_df = pd.read_csv('data/processed/categories.csv')
        category_map = dict(zip(categories_df['category_id'], categories_df['category_name']))
        category_descriptions = dict(zip(categories_df['category_id'], categories_df['category_description']))
        
        products = load_all_product_data(input_file)
        if not products:
            logger.error("No products found to process")
            return 
        
        documents = prepare_documents(products, category_map, category_descriptions)
        success = create_embeddings_and_store(documents)
        if success and run_test_search:
            print("\n=== TESTING SEARCH FUNCTIONALITY ===")
            test_search("Tôi muốn tìm một món bánh ngọt mềm, bông xốp và ngọt dịu", 3)
            test_search("Tôi đang khát nước và muốn một đồ uống mát lạnh như cà phê hoặc trà", 3)
            test_search("Tôi muốn ăn vặt một món bánh giòn rụm có vị mặn", 3)
                  
    except Exception as e:
        logger.error(f"Error in main function: {e}")
        return
    
if __name__ == "__main__":
	main('data/processed/products.csv')
    
	print("Done")