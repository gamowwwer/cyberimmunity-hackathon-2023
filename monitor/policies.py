def check_operation(id, details):
    authorized = False
    # print(f"[debug] checking policies for event {id}, details: {details}")
    print(f"[info] checking policies for event {id},"\
          f" {details['source']}->{details['deliver_to']}: {details['operation']}")
    src = details['source']
    dst = details['deliver_to']
    operation = details['operation']

    if  src == 'data_input' and dst == 'data_processor' \
        and operation == 'process_new_data':
        authorized = True

    if  src == 'data_processor' and dst == 'data_output' \
        and (operation == 'process_new_events' \
            or operation == "ALARM" \
            or operation == 'data_diff' \
            or operation == 'new_data'):
        authorized = True

    

    # kea - Kafka events analyzer - an extra service for internal monitoring,
    # can only communicate with itself
    if src == 'kea' and dst == 'kea' \
        and (operation == 'self_test' or operation == 'test_param'):
        authorized = True
    
    return authorized