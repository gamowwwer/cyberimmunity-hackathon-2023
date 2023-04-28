all: prepare build run delay5s test

delay5s:
	# can be used to let components start working
	sleep 5

sys-packages:
	sudo apt install -y docker-compose
	sudo apt install python3-pip -y
	sudo pip3 install pipenv

broker:
	docker-compose -f kafka/docker-compose.yaml up -d

pipenv:
	pipenv install -r requirements-dev.txt	

# prepare: clean sys-packages pipenv build

permissions:
	chmod u+x ./data_input/data_input.py
	chmod u+x ./data_output/data_output.py
	chmod u+x ./data_processor/data_processor.py
	chmod u+x ./monitor/monitor.py
	chmod u+x ./storage/


prepare: sys-packages permissions pipenv build run-broker

build:
	docker-compose build

run:
	docker-compose up -d

run-up:
	docker-compose up --no-start

run-broker:
	docker-compose up -d dd-zookeeper dd-broker

logs:
	docker-compose logs -f --tail 100

restart:
	docker-compose restart

run-device:
	pipenv run python device/device.py

run-system:
	pipenv run python protection_system/system.py

run-scada:
	pipenv run python scada/scada.py

run-file-server:
	export FLASK_DEBUG=1; pipenv run python ./file_server/server.py

test:
	pipenv run pytest -sv --reruns 5

clean:
	docker-compose down; pipenv --rm; rm -rf Pipfile*; echo cleanup complete

complete-check: clean prepare build delayed-test

logs:
	docker-compose logs -f --tail 100