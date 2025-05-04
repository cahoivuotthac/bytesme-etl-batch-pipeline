
from typing import List
import re

import pandas as pd

CATEGORIES_MAPPING = {
    'Cakes': ['cakes', 'dry cakes', 'cake slices', 'bánh kem bơ', 'bánh flan gato' 
              'gato cắt miếng/cupcake', 'bánh ngọt', 'gato box - cake box', 'bánh bông lan', 'bông lan'],
    
    'Breads & Buns': ['sandwiches', 'buns|savory', 'buns|sweet', 'sweet|buns', 'bánh mì', 
                      'daily storing', 'bánh tươi', 'breads', 'bánh nướng - bánh mì'],
    
    'Pastries & Pies': ['pastries-and-pies', 'donuts', 'bánh nướng', 'toasts', 'chocolate'],
    
    'Season & Specialist': ['xoài sấy', 'tết', 'bánh sinh nhật', 'trung thu', 'bánh tiệc - bánh sinh nhật'],
    
    'Cookies & Biscuits': ['cookies', 'cookie special', 'bánh healthy'],
    
    'Chilled & Cold': ['pudding', 'bánh lạnh', 'sữa chua', 'bánh entremet', 'bánh kem bắp', 'bánh mousse'],
    
    'Sets': ['set bánh tổng hợp', 'sets', 'set bánh', 'sweetbox', 'sweetin - bánh hộp thiếc cao cấp']
}

def standardize_category(df_products_name_cate: pd.DataFrame) -> List[str]:
    product_raw_cats = [str(cat).lower().strip() for cat in df_products_name_cate['original_category']]
    product_names = [str(name).lower().strip() for name in df_products_name_cate['product_name']]
    category_patterns = {
        standard_cat: '|'.join(map(re.escape, raw_cats))
        for standard_cat, raw_cats in CATEGORIES_MAPPING.items()
    }
    output_standard_cats = []
    
    for i in range(len(product_raw_cats)):
        cat_found = False 
        
        cur_cat = product_raw_cats[i] 
        if '|' in cur_cat and 'bánh tiệc - bánh sinh nhật' in cur_cat:
            output_standard_cats.append('Season & Specialist')
            continue
        
        for standard_cat, raw_cats in CATEGORIES_MAPPING.items():
            raw_cats_lower = [cat.lower() for cat in raw_cats]
            if cur_cat in raw_cats_lower:
                output_standard_cats.append(standard_cat)
                cat_found = True 
                break 
            
        if not cat_found or cur_cat == 'khác':
            for standard_cat, pattern in category_patterns.items():
                if re.search(pattern, product_names[i], re.IGNORECASE):
                    output_standard_cats.append(standard_cat)
                    cat_found = True
                    break
            
            if not cat_found:
                output_standard_cats.append('Others')
                
    return output_standard_cats


