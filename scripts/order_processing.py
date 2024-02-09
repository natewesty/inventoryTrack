from db_interact import upload_data, query_data, get_ledger_data, get_ship_location, update_disp_donum, update_disp_copperpeak
import logging

def extract_data(data, keys):
    return [data.get(key) for key in keys]

def process_order(data):
    try:
        action = data.get('action')
        process_functions = {
            'Create': create_order,
            'Update': update_order
        }
        process_function = process_functions.get(action)
        if process_function:
            process_function(data)
    except Exception as e:
        logging.error(f"Error processing order: {e}")

def create_order(data):
    try:
        payload = data.get('payload')
        purchaseType = payload.get('purchaseType')
        if purchaseType in ['Refund', 'Exchange', 'Pickup To Ship']:
            special_order(data)
        else:
            order_details = extract_data(payload, ['orderNumber', 'orderDeliveryMethod', 'paymentStatus', 'fulfillmentStatus', 'shipInventoryLocationId', 'pickupInventoryLocationId'])
            products = payload.get('products')
            for product in products:
                product_details = extract_data(product.get('product'), ['sku', 'quantity'])
                # Update the inventory for the specific location
                if order_details[1] == 'Carry Out':
                    dml_statement = f'UPDATE "Inventory" WHERE sku = {product_details[0]} AND location = {order_details[5]} SET on_hand = on_hand - {product_details[1]}'
                    update_order(dml_statement)
                    log_statement = f'INSERT INTO "InventoryLedger" (order_id, sku, location, adjustment_type, quantity, fulfillment_status) VALUES ({order_details[0]}, {product_details[0]}, {order_details[5]}, {order_details[1]}, {product_details[1]}, {order_details[3]})'
                    update_order(log_statement)
                    update_disp_donum(product_details[0], product_details[1])
                elif order_details[1] == 'Pickup':
                    dml_statement = f'UPDATE "Inventory" WHERE sku = {product_details[0]} AND location = {order_details[5]} SET awaiting_fulfillment = awaiting_fulfillment + {product_details[1]}'
                    update_order(dml_statement)
                    log_statement = f'INSERT INTO "InventoryLedger" (order_id, sku, location, adjustment_type, quantity, fulfillment_status) VALUES ({order_details[0]}, {product_details[0]}, {order_details[5]}, {order_details[1]}, {product_details[1]}, {order_details[3]})'
                    update_order(log_statement)
                else:
                    dml_statement = f'UPDATE "Inventory" WHERE sku = {product_details[0]} AND location = {order_details[4]} SET awaiting_fulfillment = awaiting_fulfillment + {product_details[1]}'
                    update_order(dml_statement)
                    log_statement = f'INSERT INTO "InventoryLedger" (order_id, sku, location, adjustment_type, quantity, fulfillment_status) VALUES ({order_details[0]}, {product_details[0]}, {order_details[4]}, {order_details[1]}, {product_details[1]}, {order_details[3]})'
                    update_order(log_statement)
    except Exception as e:
        logging.error(f"Error creating order: {e}")

def update_order(data):
    try:
        payload = data.get('payload')
        purchaseType = payload.get('purchaseType')
        if purchaseType in ['Refund', 'Exchange', 'Pickup To Ship']:
            special_order(data)
        else:
            order_details = extract_data(payload, ['orderNumber', 'orderDeliveryMethod', 'fulfillmentStatus'])
            fulfillment = get_ledger_data(order_details[0])
            if fulfillment == None:
                logging.error(f"Order {order_details[0]} not found")
                return
            elif fulfillment == 'Fulfilled':
                logging.error(f"Order {order_details[0]} already fulfilled")
                return
            else:
                products = payload.get('products')
                for product in products:
                    product_details = extract_data(product.get('product'), ['sku', 'quantity'])
                    if order_details[2] == 'No Fulfillment Required':
                        dml_statement = f'UPDATE "Inventory" WHERE sku = {product_details[0]} AND location = {order_details[4]} SET awaiting_fulfillment = awaiting_fulfillment - {product_details[1]}'
                        update_order(dml_statement)
                    elif order_details[1] == 'Carry Out' or order_details[1] == 'Pickup':
                        dml_statement = f'UPDATE "Inventory" WHERE sku = {product_details[0]} AND location = {order_details[5]} SET on_hand = on_hand - {product_details[1]} and awaiting_fulfillment = awaiting_fulfillment - {product_details[1]}'
                        update_order(dml_statement)
                        update_disp_donum(product_details[0], product_details[1])
                    else:
                        dml_statement = f'UPDATE "Inventory" WHERE sku = {product_details[0]} AND location = {order_details[4]} SET awaiting_fulfillment = awaiting_fulfillment + {product_details[1]}'
                        update_order(dml_statement)
                    log_statement = f'INSERT INTO "InventoryLedger" (order_id, sku, location, adjustment_type, quantity, fulfillment_status) VALUES ({order_details[0]}, {product_details[0]}, {get_ship_location(order_details[1])}, {order_details[1]}, {product_details[1]}, {order_details[2]})'
                    update_order(log_statement)
                    update_disp_copperpeak(product_details[0], product_details[1])
    except Exception as e:
        logging.error(f"Error updating order: {e}")
        
def special_order(data):
    try:
        payload = data.get('payload')
        purchaseType = payload.get('purchaseType')
        for purchaseType in payload:
            order_details = extract_data(payload, ['orderNumber', 'orderDeliveryMethod', 'paymentStatus', 'fulfillmentStatus'])
            products = payload.get('products')
            for product in products:
                product_details = extract_data(product.get('product'), ['sku', 'quantity'])
                location = get_ship_location(order_details[1])
                if purchaseType == 'Refund' and order_details[3] == 'Not Fulfilled':
                    dml_statement = f'UPDATE "Inventory" WHERE sku = {product_details[0]} AND location = {location} SET awaiting_fulfillment = awaiting_fulfillment - {product_details[1]}'
                    update_order(dml_statement)
                elif purchaseType == 'Refund' and order_details[3] != 'Not Fulfilled':
                    break
                elif purchaseType == 'Exchange':
                    dml_statement = f'UPDATE "Inventory" WHERE sku = {product_details[0]} AND location = {location} SET on_hand = on_hand + {product_details[1]}'
                    update_order(dml_statement)  
                    update_disp_donum(product_details[0], product_details[1])                 
                elif purchaseType == 'Pickup To Ship':
                    dml_statement = f'UPDATE "Inventory" WHERE sku = {product_details[0]} AND location = {get_ship_location("Pickup")} SET awaiting_fulfillment = awaiting_fulfillment - {product_details[1]}'
                    update_order(dml_statement)
                    pts_statement = f'UPDATE "Inventory" WHERE sku = {product_details[0]} AND location = {get_ship_location("Ship")} SET awaiting_fulfillment = awaiting_fulfillment + {product_details[1]}'
                # Add the order to the ledger
                log_statement = f'INSERT INTO "InventoryLedger" (order_id, sku, location, adjustment_type, quantity, fulfillment_status) VALUES ({order_details[0]}, {product_details[0]}, {location}, {purchaseType}, {product_details[1]}, {order_details[3]})'
                update_order(log_statement)
    except Exception as e:
        logging.error(f"Error processing special order: {e}")