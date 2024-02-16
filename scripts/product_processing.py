import logging
from .db_interact import upload_data
from .order_processing import extract_data

def process_product(data):
    """
    Processes a product webhook.

    Parameters:
    data (dict): The product data.
    """
    try:
        action = data.get('action')
        process_functions = {
            'Create': create_product,
            'Update': update_product
        }
        process_function = process_functions.get(action)
        if process_function:
            process_function(data)
    except Exception as e:
        logging.error(f"Error processing product: {e}")

def create_product(data):
    """
    Creates a new product in the database.

    Parameters:
    data (dict): The product data.
    """
    try:
        payload = data.get('payload')
        product_details = extract_data(payload, ['id', 'sku', 'title'])
        dml_statement = f'INSERT INTO "Products" (id, sku, label) VALUES (%s, %s, %s);'
        update_order(dml_statement, (product_details[0], product_details[1], product_details[2]))
    except Exception as e:
        logging.error(f"Error creating product: {e}")

def update_product(data):
    """
    Updates an existing product in the database.

    Parameters:
    data (dict): The product data.
    """
    try:
        variants = data.get('payload').get('variants')
        for variant in variants:
            upID = extract_data(variant, ['id', 'sku'])
            inventories = variant.get('inventory')
            for inventory in inventories:
                location = inventory.get('inventoryLocationID')
                OHamount = inventory.get('availableForSaleCount') + inventory.get('reserveCount') + inventory.get('allocatedCount')
                AFamount = inventory.get('allocatedCount')
                ASamount = inventory.get('availableForSaleCount') + inventory.get('reserveCount')
                
                # Check if the ID exists in the Inventory table
                query = f'SELECT COUNT(*) FROM "Inventory" WHERE id = %s AND location = %s;'
                count = query_data(query, (upID[0], location))

                if count[0] > 0:
                    # The ID exists, update the quantities
                    dml_statement = f'UPDATE "Inventory" SET on_hand = %s, awaiting_fulfillment = %s, available_to_sell = %s WHERE id = %s AND location = %s;'
                    update_order(dml_statement, (OHamount, AFamount, ASamount, upID[0], location))
                else:
                    # The ID does not exist, insert a new row
                    dml_statement = f'INSERT INTO "Inventory" (id, location, on_hand, awaiting_fulfillment, available_to_sell) VALUES (%s, %s, %s, %s, %s);'
                    update_order(dml_statement, (upID[0], location, OHamount, AFamount, ASamount))

                # Check if the SKU exists in the InventoryDisp table
                query = f'SELECT COUNT(*) FROM "InventoryDisp" WHERE sku = %s AND location = %s;'
                count = query_data(query, (upID[1], location))

                if count[0] > 0:
                    # The SKU exists, update the on_hand quantity
                    dml_statement_disp = f'UPDATE "InventoryDisp" SET on_hand = %s WHERE sku = %s AND location = %s;'
                    update_order(dml_statement_disp, (OHamount, upID[1], location))
                else:
                    # The SKU does not exist, insert a new row
                    dml_statement_disp = f'INSERT INTO "InventoryDisp" (sku, location, on_hand, awaiting_fulfillment, available_to_sell) VALUES (%s, %s, %s, 0, 0);'
                    update_order(dml_statement_disp, (upID[1], location, OHamount))
    except Exception as e:
        logging.error(f"Error updating product: {e}")
