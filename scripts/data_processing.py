import sqlalchemy
import logging
from sqlalchemy import text
from .db_interact import upload_data, query_data, get_ledger_data, get_ship_location, update_disp

######## NEED TO UPDATE DB TO REFLECT NEW TABLES ########
    
# Define the location aliases
location_aliases = {
'Donum': 'bottles_donum',
'Copper Peak': 'bottles_copperpeak',
'Groskopf': 'bottles_groskopf',
# Add more aliases as needed
}

def extract_data(data, keys):
    return [data.get(key) for key in keys]

def phys_move(sku, location, quantity, order_id, delivery):
    try:
        # Preprocess the location
        alias = location_aliases.get(location, location) 
        
        # Create the statements
        inven_statement = text(f'UPDATE "Inventory" SET on_hand = on_hand - :quantity WHERE sku = :sku AND location = :location')
        ledger_statement = text(f'INSERT INTO "InventoryLedger" (order_id, sku, location, adjustment_type, quantity, fulfillment_status) VALUES (:order_id, :sku, :location, :delivery, :quantity, "Fulfilled")')            
        disp_statement = text(f'UPDATE "InventoryDisp" SET on_hand = on_hand - :quantity WHERE sku = :sku AND location = :alias')
        
        # Execute the uploads
        upload_data(inven_statement, params={"quantity": quantity, "sku": sku, "location": location}) # Update the inventory
        upload_data(ledger_statement, params={"order_id": order_id, "sku": sku, "location": location, "adjustment_type": delivery, "quantity": quantity, "fulfillment_status": "Fulfilled"}) # Update the ledger
        upload_data(disp_statement, params={"quantity": quantity, "sku": sku, "location": alias}) # Update the display
    except Exception as e:
        logging.error(f"Error in phys_move: {e}")

def sell_sleep(sku, location, quantity, order_id, delivery):
    try:            
        # Create the statements
        inven_statement = text(f'UPDATE "Inventory" SET awaiting_fulfillment = awaiting_fulfillment + :quantity WHERE sku = :sku AND location = :location')
        ledger_statement = text(f'INSERT INTO "InventoryLedger" (order_id, sku, location, adjustment_type, quantity, fulfillment_status) VALUES (:order_id, :sku, :location, :delivery, :quantity, "Pending")')            
        
        # Execute the uploads
        upload_data(inven_statement, params={"quantity": quantity, "sku": sku, "location": location}) # Update the inventory
        upload_data(ledger_statement, params={"order_id": order_id, "sku": sku, "location": location, "adjustment_type": delivery, "quantity": quantity, "fulfillment_status": "Pending"}) # Update the ledger
    except Exception as e:
        logging.error(f"Error in sell_sleep: {e}")
        
def sell_wake(sku, location, quantity, order_id):
    try:
        # Create the statement
        inven_statement = text(f'UPDATE "Inventory" SET awaiting_fulfillment = awaiting_fulfillment - :quantity WHERE sku = :sku AND location = :location')         
        
        # Execute the upload
        upload_data(inven_statement, params={"quantity": quantity, "sku": sku, "location": location}) # Update the inventory
    except Exception as e:
        logging.error(f"Error in sell_wake: {e}")
        
def order_null(sku, location, quantity, order_id, delivery):
    try:
        # Create the statement
        ledger_statement(text(f'INSERT INTO "InventoryLedger" (order_id, sku, location, adjustment_type, quantity, fulfillment_status) VALUES (:order_id, :sku, :location, :delivery, :quantity, "Refunded Before Fulfillment")'))
        
        # Execute the upload
        upload_data(ledger_statement, params={"order_id": order_id, "sku": sku, "location": location, "adjustment_type": delivery, "quantity": quantity, "fulfillment_status": "Refunded Before Fulfillment"}) # Update the ledger
    except Exception as e:
        logging.error(f"Error in order_null: {e}")
        
def bundle_check(sku, quantity, orderNumber, del_method):
    try:
        bundle_statement = text(f'SELECT * FROM "Bundles" WHERE bundle_sku = :sku')
        bundle_data = query_data(bundle_statement, params={"sku": sku})

        if bundle_data:
            return True
        else:
            return False
    except Exception as e:
        logging.error(f"Error in bundle_check: {e}")
        return
    
def bundle_process(sku, quantity, orderNumber, del_method):  
    try:
        bundle_statement = text(f'SELECT * FROM "Bundles" WHERE bundle_sku = :sku')
        bundle_data = query_data(bundle_statement, params={"sku": sku})

        if bundle_data:
            for row in bundle_data:
                for i in range(1, 8):
                    sku_key = f'sku{i}'
                    quantity_key = f'quantity{i}'

                    if row[sku_key] is None or row[quantity_key] is None:
                        break

                    sku = row[sku_key]
                    quantity = row[quantity_key] * bundle_quantity
                    if del_method == 'Carry Out':
                        phys_move(sku, 'Donum', quantity, orderNumber, del_method) 
                    elif del_method == 'Pickup':
                        sell_sleep(sku, 'Donum', quantity, orderNumber, del_method)
                    else:
                        sell_sleep(sku, 'Copper Peak', quantity, orderNumber, del_method)

    except Exception as e:
        logging.error(f"Error in process_bundle: {e}")
        