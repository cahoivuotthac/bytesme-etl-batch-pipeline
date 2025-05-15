import os
import yaml

def load_config(path):
	base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
	config_dir_name = os.path.basename(os.path.dirname(os.path.abspath(__file__)))
	config_path = os.path.join(base_dir, config_dir_name, path)
	
	try:
		with open(config_path, 'r') as f: 
			config = yaml.safe_load(f)
		
		return config	
	except FileNotFoundError:
		raise FileNotFoundError(f"Configuration file not found: {config_path}")