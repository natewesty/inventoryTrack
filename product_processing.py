import logging
from db_interact import upload_data
from order_processing import extract_data

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
        dml_statement = f'INSERT INTO "Products" (id, sku, label) VALUES ({product_details[0]}, {product_details[1]}, {product_details[2]})'
        upload_data(dml_statement)
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
                dml_statement = f'UPDATE "Inventory" WHERE id = {upID[0]} AND location = {location} SET on_hand = {OHamount}, awaiting_fulfillment = {AFamount}, available_to_sell = {ASamount}'
                upload_data(dml_statement)                
    except Exception as e:
        logging.error(f"Error updating product: {e}")