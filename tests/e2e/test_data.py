from pytest import fixture
from time import sleep
import json
from urllib.request import urlopen, Request
import docker


DATA_INPUT_URL = "http://localhost:6051/ingest"
DATA_OUTPUT_URL = "http://localhost:6053/alerts"
AUTH_TOKEN = 'very-secure-token'

RAW_TEST_FIELD_DATA = {
    "value": 15
}

OVERLOAD_DATA = {
    "value": 21
}

ZERO_VALUE_DATA = {
    "value": 0
}

HEADERS = {
    'content-type': 'application/json',
    'auth': AUTH_TOKEN
}


def stop_sensor():
    client = docker.from_env()
    cont_name = client.containers.list(all=True, filters={"name": "sensor"})[0].name
    container = client.containers.get(cont_name)
    if container.status != "exited":
        container.stop()
    assert container.status == "exited"


def send_raw_data(data: dict) -> dict:
    req = Request(
        DATA_INPUT_URL,
        data=json.dumps(data).encode(),
        headers=HEADERS
    )
    response = urlopen(req)
    assert response.getcode() == 200
    result = json.loads(response.read().decode())
    id = result["id"]
    return id, result

def request_new_alerts() -> list:
    req = Request(DATA_OUTPUT_URL, headers=HEADERS)
    response = urlopen(req)
    assert response.getcode() == 200
    return json.loads(response.read().decode())

def zero_processor():
    for _ in range(3):
        id, result = send_raw_data(ZERO_VALUE_DATA)
        assert result["operation"] == "new data received"

def test_detect_discrete_alerts():
    stop_sensor()
    zero_processor()
    sleep(2)
    request_new_alerts()

    id, result = send_raw_data(OVERLOAD_DATA)
    assert result["operation"] == "new data received"

    retries = 20
    while retries > 0:
        sleep(0.5)
        alerts = request_new_alerts()
        if alerts != []:
            break
        else:
            retries -= 1

    assert retries > 0
    assert len(alerts) == 1

    for alert in alerts:
        assert alert["source_id"] == id
        assert alert["event"] == "high_diff"


def test_alarm_alert():
    request_new_alerts()

    id, result = send_raw_data(OVERLOAD_DATA)
    assert result["operation"] == "new data received"

    retries = 20
    while retries > 0:
        sleep(0.5)
        alerts = request_new_alerts()
        if alerts != []:
            break
        else:
            retries -= 1

    assert retries > 0
    assert len(alerts) == 2

    alert = alerts[0]
    assert alert["source_id"] == id
    assert alert["event"] == "overflow"

