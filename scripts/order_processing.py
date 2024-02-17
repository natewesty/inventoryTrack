import logging
import sqlalchemy
from sqlalchemy import text
from .db_interact import get_ledger_data, get_ship_location, query_data
from .data_processing import phys_move, sell_sleep, sell_wake, order_null, extract_data, bundle_check, bundle_process

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
        # Check for special order types
        purchaseType = payload.get('purchaseType')
        if purchaseType in ['Refund', 'Exchange', 'Pickup To Ship']:
            special_order(data)
        else:
            # Process inventory moves by sku
            order_details = extract_data(payload, ['orderNumber', 'orderDeliveryMethod'])
            products = payload.get('products')
            for product in products:
                product_details = extract_data(product.get('product'), ['sku', 'quantity'])
                if bundle_check(*product_details, *order_details) == True:
                    bundle_process(*product_details, *order_details)
                elif order_details[1] == 'Carry Out':
                    phys_move(product_details[0], 'Donum', product_details[1], order_details[0], order_details[1]) 
                elif order_details[1] == 'Pickup':
                    sell_sleep(product_details[0], 'Donum', product_details[1], order_details[0], order_details[1])
                else:
                    sell_sleep(product_details[0], 'Copper Peak', product_details[1], order_details[0], order_details[1])
    except Exception as e:
        logging.error(f"Error creating order: {e}")

def update_order(data):
    try:
        payload = data.get('payload')
        # Check for special order types
        purchaseType = payload.get('purchaseType')
        if purchaseType in ['Refund', 'Exchange', 'Pickup To Ship']:
            special_order(data)
        else:
            order_details = extract_data(payload, ['orderNumber', 'orderDeliveryMethod', 'fulfillmentStatus'])
            # Check order fulfillment status
            fulfillment = get_ledger_data(order_details[0])
            if fulfillment == None:
                logging.error(f"Order {order_details[0]} not found")
                return
            elif fulfillment == 'Fulfilled':
                logging.error(f"Order {order_details[0]} already fulfilled")
                return
            else:
                # Process inventory moves by sku
                products = payload.get('products')
                for product in products:
                    product_details = extract_data(product.get('product'), ['sku', 'quantity'])
                    # Check for bundles and process accordingly
                    if bundle_check(*product_details, order_details[0], order_details[1]) == True:
                        bundle_process(*product_details, order_details[0], order_details[1])
                        continue
                    # Process non-bundle inventory moves
                    if order_details[2] == 'No Fulfillment Required':
                        location = get_ship_location(order_details[1])
                        sell_wake(product_details[0], location, product_details[1], order_details[0], order_details[1])
                    elif order_details[1] == 'Pickup' and (order_details[2] == 'Fulfilled' or order_details[2] == 'Partially Fulfilled'):
                        phys_move(product_details[0], 'Donum', product_details[1], order_details[0], order_details[1])
                        sell_wake(product_details[0], 'Donum', product_details[1], order_details[0])
                    elif order_details[1] == 'Ship' and (order_details[2] == 'Fulfilled' or order_details[2] == 'Partially Fulfilled'):
                        phys_move(product_details[0], 'Copper Peak', product_details[1], order_details[0], order_details[1])
                        sell_wake(product_details[0], 'Copper Peak', product_details[1], order_details[0])
                    else:
                        break
    except Exception as e:
        logging.error(f"Error updating order: {e}")
        
def special_order(data):
    try:
        payload = data.get('payload')
        order_details = extract_data(payload, ['orderNumber', 'orderDeliveryMethod', 'fulfillmentStatus', 'purchaseType'])
        products = payload.get('products')
        for product in products:
            product_details = extract_data(product.get('product'), ['sku', 'quantity'])
            location = get_ship_location(order_details[1])
            # Check for bundles and process accordingly
            if bundle_check(*product_details, order_details[0], order_details[1]) == True:
                bundle_process(*product_details, order_details[0], order_details[1])
                continue
            # Process non-bundle inventory moves
            if order_details[3] == 'Refund' and order_details[2] == 'Not Fulfilled':
                sell_wake(product_details[0], location, product_details[1], order_details[0])
                order_null(product_details[0], location, product_details[1], order_details[0], order_details[3])
            elif order_details[3] == 'Refund' and order_details[2] != 'Not Fulfilled':
                break
            elif order_details[3] == 'Exchange':
                phys_move(product_details[0], location, product_details[1], order_details[0], order_details[3])
            elif order_details[3] == 'Pickup To Ship':
                sell_wake(product_details[0], 'Donum', product_details[1], order_details[0])
                sell_sleep(product_details[0], 'Copper Peak', product_details[1], order_details[0], order_details[3])
    except Exception as e:
        logging.error(f"Error processing special order: {e}")
