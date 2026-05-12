.PHONY: build check pages-build serve watch dev docker-up docker-down clean

INVENTORY_XLSM ?= Rental-Database.xlsm

build:
	INVENTORY_XLSM="$(INVENTORY_XLSM)" python3 scripts/convert_inventory.py

check: build
	INVENTORY_XLSM="$(INVENTORY_XLSM)" python3 scripts/convert_inventory.py --check
	python3 -m json.tool data/inventory.json > /dev/null
	python3 -m json.tool data/category-order.json > /dev/null

pages-build:
	test -f data/inventory.json
	test -f data/category-order.json
	python3 -m json.tool data/inventory.json > /dev/null
	python3 -m json.tool data/category-order.json > /dev/null
	rm -rf dist
	mkdir -p dist
	cp index.html dist/
	cp -R assets data dist/
	touch dist/.nojekyll

serve: build
	python3 -m http.server 8000

watch:
	INVENTORY_XLSM="$(INVENTORY_XLSM)" python3 scripts/watch_inventory.py

dev:
	INVENTORY_XLSM="$(INVENTORY_XLSM)" python3 scripts/dev_server.py

docker-up:
	docker compose up --build

docker-down:
	docker compose down

clean:
	rm -f data/inventory.json
