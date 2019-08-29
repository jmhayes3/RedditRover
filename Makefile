.PHONY: clean

clean:
	find . -name '__pycache__' -exec rm -rf {} +
	rm -f ./config/storage.db
