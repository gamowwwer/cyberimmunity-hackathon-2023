# implements Kafka topic consumer functionality

from email.mime import base
import threading
from confluent_kafka import Consumer, OFFSET_BEGINNING
import json
from producer import proceed_to_deliver
from urllib.request import urlopen
from uuid import uuid4
import base64
from collections import deque

CURRENT_THRESHOLD = 20
DELTA_THRESHOLD = 19

MSG_MAPPING = {
    "overflow": {
        "operation": "ALARM",
        "ouput_port": "protection"
    },
    "high_diff": {
        "operation": "data_diff",
        "ouput_port": "scada"
    }
}

DATA_ARRAY = deque((0, 0, 0))

def check_new_data(data: list, details):
    # details["alerts"] =  []
    alerts = []
    for sample in data:
        if "value" in sample:
            current = data[sample]
            DATA_ARRAY.append(current)
            DATA_ARRAY.popleft()
            delta = max(DATA_ARRAY) - min(DATA_ARRAY)
            current_vote_threshold = [True if value > CURRENT_THRESHOLD else False for value in DATA_ARRAY]
            votes_count = current_vote_threshold.count(True)
            if votes_count >= 2:
                # details["alerts"].append(
                alerts.append(
                    {
                        "source_id": details["id"],
                        "event": "overflow",
                        "current_value": current,
                        "current_threshold": CURRENT_THRESHOLD
                    }
                )
            
            if delta > DELTA_THRESHOLD:
                # details["alerts"].append(
                alerts.append(
                    {
                        "source_id": details["id"],
                        "event": "high_diff",
                        "current_value": current,
                        "current_threshold": CURRENT_THRESHOLD
                    }
                )
    return alerts


def handle_event(id: str, details: dict):
    """
    Обрабатываем входящие события:
        Если Последние два из трех измерений превышают CURRENT_THRESHOLD, 
        то отправляем сигналы в систему защиты и делаем запись в журнале 

        Если Последние два из трех измерений различаются больше чем на DELTA_THRESHOLD, 
        то отправляем сигналы в АСУ ТП и делаем запись в журнале 
    """
    # print(f"[debug] handling event {id}, {details}")
    print(f"[info] handling event {id}, {details['source']}->{details['deliver_to']}: {details['operation']}")
    try:
        if details['operation'] == 'process_new_data':
            new_data = details["new_data"]
            alerts = check_new_data(new_data, details)
            details["deliver_to"] = "data_output"

            if len(alerts) > 0:
                # new alerts need to be delivered
                for alert in alerts:
                    event_type = alert["event"]
                    new_req_id = uuid4().__str__()
                    new_message = {
                        "id": new_req_id,
                        "source": {id},
                        "operation": MSG_MAPPING[event_type]["operation"],  # "ALARM", "data_diff"
                        "data": alert,
                        "deliver_to": "data_output",
                        "output_port": MSG_MAPPING[event_type]["ouput_port"]  # "protection", "scada"

                    }
                    # Отправляем в систему-потребитель
                    print(f"[info] sending {new_message['operation']} to {new_message['output_port']}")
                    print(new_req_id)
                    print(new_message)
                    proceed_to_deliver(new_req_id, new_message)

                    # Отправляем событие в журнал
                    journal_req_id = uuid4().__str__()
                    journal_message = new_message.copy()
                    journal_message["id"] = journal_req_id
                    journal_message["deliver_to"] = "journal"
                    print(f"[info] sending {journal_message['operation']} to journal")
                    print(journal_req_id)
                    print(journal_message)
                    proceed_to_deliver(journal_req_id, journal_message)

            # Отправляем значения в scada
            data_req_id = uuid4().__str__()
            data_message = {
                "id": data_req_id,
                "source": {id},
                "operation": "new_data",
                "data": new_data,
                "deliver_to": "data_output",
                "output_port": "scada"
            }
            print(f"[info] sending {data_message['operation']} to scada")
            print(data_req_id)
            print(data_message)
            proceed_to_deliver(data_req_id, data_message)
    except Exception as e:
        print(f"[error] failed to handle request: {e}")

def consumer_job(args, config):
    # Create Consumer instance
    downloader_consumer = Consumer(config)

    # Set up a callback to handle the '--reset' flag.
    def reset_offset(downloader_consumer, partitions):
        if args.reset:
            for p in partitions:
                p.offset = OFFSET_BEGINNING
            downloader_consumer.assign(partitions)

    # Subscribe to topic
    topic = "data_processor"
    downloader_consumer.subscribe([topic], on_assign=reset_offset)

    # Poll for new messages from Kafka and print them.
    try:
        while True:
            msg = downloader_consumer.poll(1.0)
            if msg is None:
                # Initial message consumption may take up to
                # `session.timeout.ms` for the consumer group to
                # rebalance and start consuming
                # print("Waiting...")
                pass
            elif msg.error():
                print(f"[error] {msg.error()}")
            else:
                # Extract the (optional) key and value, and print.
                try:
                    id = msg.key().decode('utf-8')
                    details_str = msg.value().decode('utf-8')
                    # print("[debug] consumed event from topic {topic}: key = {key:12} value = {value:12}".format(
                        # topic=msg.topic(), key=id, value=details_str))
                    handle_event(id, json.loads(details_str))
                except Exception as e:
                    print(
                        f"Malformed event received from topic {topic}: {msg.value()}. {e}")
    except KeyboardInterrupt:
        pass
    finally:
        # Leave group and commit final offsets
        downloader_consumer.close()


def start_consumer(args, config):
    threading.Thread(target=lambda: consumer_job(args, config)).start()


if __name__ == '__main__':
    start_consumer(None)
