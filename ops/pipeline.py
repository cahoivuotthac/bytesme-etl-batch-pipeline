import argparse
import glob
import os
from typing import Any, Dict, List

import pandas as pd
import yaml
from config.logger_config import setup_logger, setup_discord_notification

from ops.transform.generate_mock_data import update_product_dataset
from ops.transform.remove_duplicates import remove_duplicates
from ops.transform.standardize_categories import standardize_category
from ops.transform.seperate_tables import seperate_tables

logger = setup_logger("transform_pipeline.log")
setup_discord_notification(logger)
class TransformPipeline:
	def __init__(self, config_path: str = "config/etl_config.yml"):
		self.config = self._load_config(config_path)
		self.input_dir = self.config.get('input_directory', "data/raw")
		self.output_staging_dir = self.config.get("output_directory", "data/staging")
		self.output_processed_dir = self.config.get("final_output_directory", "data/processed")
		self.transforms = self.config.get("transforms", [])
  
	def _load_config(self,	config_path: str) -> Dict[str, Any]:
		try:
			with open(config_path, 'r') as f: 
				return yaml.safe_load(f)
		except FileNotFoundError: 
			logger.warning(f"Config file {config_path} not found. Using defaults.")
			return {
				"input_directory": "data/raw",
                "output_directory": "data/processed",
                "transforms": ["standardize_categories", "remove_duplicates", "generate_mock_data"],
                "file_pattern": "*.csv"
			}
   
	def _get_input_file(self) -> List[str]:
		pattern = self.config.get("file_pattern", "*.csv")
		files = glob.glob(os.path.join(self.input_dir, pattern))
		logger.info(f"Found {len(files)} input files: {files}")
		return files
    
	def process_file(self, input_file: str) -> str:
		file_name = os.path.basename(input_file)
		output_staging_file = os.path.join(self.output_staging_dir, file_name)
		
		df = pd.read_csv(input_file)
		
		logger.info(f"Processing file: {input_file}")

		for transform in self.transforms:
			logger.info(f"Applying transformation: {transform}")

			if transform == "standardize_categories":
				if 'original_category' in df.columns:
					logger.info("Column original_category is found!")
				input_df = df[['product_name', 'original_category']]
				categories = standardize_category(input_df)
				df['category_name'] = categories 
				if 'category_name' in df.columns:
					logger.info(f"Adding category_name succesfully")
				df = df.drop(columns=['original_category'])
				
			elif transform == "remove_duplicates":
				original_len = len(df)
				df = remove_duplicates(df)
				logger.info(f"Removed {original_len - len(df)} duplicated records")
				
			elif transform == 'generate_mock_data':
				mock_cols = ['product_code', 'product_total_ratings', 'product_description',
                                'product_overall_stars', 'product_total_orders', 'product_price']

				columns_to_update = [col for col in mock_cols if col in df.columns]
				
				if columns_to_update:
					df = update_product_dataset(df, output_staging_file) 

				df.to_csv(self.output_staging_dir)
			elif transform == 'seperate_tables':
    
				rs = seperate_tables(self.output_staging_dir, self.output_processed_dir)
				logger.info(f"Result of seperating tables: {rs}")

		df.to_csv(output_staging_file, index=False)
		logger.info(f"Saved processed file to {output_staging_file}")
  
		return output_staging_file

	def run(self):
		input_files = self._get_input_file()
		results = []

		for input_file in input_files:
			try:
				output_file = self.process_file(input_file)
				results.append({
					"input": input_file,
					"output": output_file,
					"status": "success"
				})
			except Exception as e:
				logger.error(f"Error processing {input_file}: {str(e)}")
				results.append({
					"input": input_file,
					"status": "error",
					"message": str(e)
				})
		success_count = sum(1 for r in results if r["status"] == "success")
		logger.info(f"Pipeline completed: {success_count}/{len(results)} files processed successfully")
		logger.info(f"Check result: {results}")
		return results

def main():
	parser = argparse.ArgumentParser(description="Run transformation pipeline on CSV files")
	parser.add_argument("--config", default="config/etl_config.yml", help="Path to config YAML file")
	parser.add_argument("--file", help="Process a specific file instead of all files")
	args = parser.parse_args()

	pipeline = TransformPipeline(args.config)

	if args.file:
		# Process a specific file
		try:
			result = pipeline.process_file(args.file)
			logger.info(f"Processed {args.file} -> {result}")
		except Exception as e:
			logger.error(f"Failed to process {args.file}: {str(e)}")
			return 1
	else:
		# Process all files
		pipeline.run()

	return 0	

if __name__ == "__main__":
    exit(main())