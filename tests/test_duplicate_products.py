import csv 
import os

import pandas as pd 

def print_duplicate_lines(filepath):
    lines = []
    duplicate_lines = []
    
    with open(filepath, 'r') as f:
        reader = csv.reader(f)
        header = next(reader)
        
        for line in reader:
            if line in lines:
                duplicate_lines.append(line)
            else:
                lines.append(line)
    return duplicate_lines, header

src_filepath = 'data/raw/drink_products.csv'
des_filepath = 'data/staging/drink_products.csv' 
duplicate_lines, header = print_duplicate_lines(src_filepath)
if duplicate_lines and header:
    df = pd.DataFrame(data=duplicate_lines, columns=header)
    df.to_csv(des_filepath, index=False, encoding='utf-8')
     