# implements Kafka topic consumer functionality

import multiprocessing
import threading
from confluent_kafka import Consumer, OFFSET_BEGINNING
import json
import requests

_events_queue: multiprocessing.Queue or None = None

CONTENT_HEADER = {"Content-Type": "application/json"}


#порт контакта с защитой
def out_alarm():
    data = {"status": True}
    try:
        requests.post(
            "http://protection:6068/alarm",
            data=json.dumps(data),
            headers=CONTENT_HEADER,
        )
    except Exception as e:
        print(f"[ERROR] Failed to deliver message to protection system: {e}")

#цифровой порт
def out_warning(msg):
    try:
        requests.post(
            "http://scada:6069/warning",
            data=json.dumps(msg),
            headers=CONTENT_HEADER,
        )
    except Exception as e:
        print(f"[ERROR] Failed to deliver message to scada: {e}")

def out_d(msg):
    try:
        data = msg["data"]
        requests.post(
            "http://scada:6069/data_d",
            data=json.dumps(data),
            headers=CONTENT_HEADER,
        )
    except Exception as e:
        print(f"[ERROR] Failed to deliver new data to scada: {e}")


def handle_event(id: str, details: dict):
    print(f"[info] handling event {id}, {details['source']}->{details['deliver_to']}: {details['operation']}")
    # if details["operation"] == "process_new_events":
        # _events_queue.put(details)
    output_port = details["output_port"]
    operation = details["operation"]
    if output_port == "protection":
        if operation == "ALARM":
            print(f"[info] sending ALARM to protection")
            _events_queue.put(details)
            out_alarm()
    elif output_port == "scada":
        if details["operation"] == "data_diff":
            print(f"[info] sending data_diff to scada")
            _events_queue.put(details)
            out_warning(details)
        elif details["operation"] == "new_data":
            print(f"[info] sending new_data to scada")
            out_d(details)
            _events_queue.put(details)

def consumer_job(args, config, events_queue):

    global _events_queue
    _events_queue = events_queue

    # Create Consumer instance
    manager_consumer = Consumer(config)

    # Set up a callback to handle the '--reset' flag.
    def reset_offset(manager_consumer, partitions):
        if args.reset:
            for p in partitions:
                p.offset = OFFSET_BEGINNING
            manager_consumer.assign(partitions)

    # Subscribe to topic
    topic = "data_output"
    manager_consumer.subscribe([topic], on_assign=reset_offset)

    # Poll for new messages from Kafka and print them.
    try:
        while True:
            msg = manager_consumer.poll(1.0)
            if msg is None:
                # Initial message consumption may take up to
                # `session.timeout.ms` for the consumer group to
                # rebalance and start consuming
                # print("Waiting...")
                pass
            elif msg.error():
                print(f"[error] {msg.error()}")
            else:
                try:
                    id = msg.key().decode('utf-8')
                    details = json.loads(msg.value().decode('utf-8'))
                    handle_event(id, details)
                except Exception as e:
                    print(
                        f"[error] malformed event received from topic {topic}: {msg.value()}. {e}")    
    except KeyboardInterrupt:
        pass
    finally:
        # Leave group and commit final offsets
        manager_consumer.close()

def start_consumer(args, config, events_queue):
    threading.Thread(target=lambda: consumer_job(args, config, events_queue)).start()
    
if __name__ == '__main__':
    start_consumer(None)
