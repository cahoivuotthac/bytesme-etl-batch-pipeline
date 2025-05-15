.PHONY: transform transform-file clean

transform:
	python3 -m ops.pipeline

# ex: make transform-file FILE=data/raw/your_file.csv
transform-file:
	python3 -m ops.pipeline --file $(FILE)

clean:
	rm -rf data/processed/*.csv

# database connect 
to_psql:
	