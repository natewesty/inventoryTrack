import logging
import sqlalchemy
from sqlalchemy import text
from .db_interact import upload_data
from .data_processing import extract_data

def process_product(data):
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
    try:
        payload = data.get('payload')
        if payload.get('type') == 'Bundle':
            bundle_sku = payload.get('variants').get('sku')
            bundleItems = payload.get('bundleItems')
            b = 1
            for i in bundleItems:
                bundleItem = extract_data(item, ['sku', 'quantity'])
                dml_statement = text(f'INSERT INTO "Bundles" (sku{b}, quantity{b}, bundle_sku) VALUES (:sku, :quantity, :bundle_sku);')
                upload_data(dml_statement, params={"sku": bundleItem[0], "quantity":bundleItem[1], "bundle_sku": bundle_sku})
                b += 1
        else:
            variants = payload.get('variants')
            for variant in variants:
                new_item = extract_data(variant, ['id', 'sku', 'title'])
                query_statement = text(f'SELECT id FROM "Products" WHERE id = :id')
                result = query_data(query_statement, params={"id":new_item[0]})
                if result:
                    logging.error(f"Product {new_item[0]} already exists")
                    return
                else:
                    dml_statement = text(f'INSERT INTO "Products" (id, sku, label) VALUES (id, sku, label);')
                    upload_data(dml_statement, params={"id": new_item[0], "sku": new_item[1], "label": new_item[2]})
    except Exception as e:
        logging.error(f"Error creating product: {e}")

def update_product(data):
    try:
        payload = data.get('payload')
        if payload.get('type') == 'Bundle':
            bundle_sku = payload.get('variants').get('sku')
            bundleItems = payload.get('bundleItems')
            for item in bundleItems:
                bundleItem = extract_data(item, ['sku', 'quantity'])
                dml_statement = text(f'UPDATE "Bundles" SET quantity = :quantity WHERE sku = :sku AND bundle_sku = :bundle_sku;')
                upload_data(dml_statement, params={"quantity": bundleItem[1], "sku": bundleItem[0], "bundle_sku": bundle_sku})
        else:
            variants = payload.get('variants')
            for variant in variants:
                updated_item = extract_data(variant, ['id', 'sku', 'title'])
                dml_statement = text(f'UPDATE "Products" SET sku = :sku, label = :label WHERE id = :id;')
                upload_data(dml_statement, params={"sku": updated_item[1], "label": updated_item[2], "id": updated_item[0]})
    except Exception as e:
        logging.error(f"Error updating product: {e}")
