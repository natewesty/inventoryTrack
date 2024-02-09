import os
from google.cloud import spanner

def upload_data(dml_statement):
    spanner_client = spanner.Client()
    instance_id = 'inventory'
    instance = spanner_client.instance(instance_id)
    database_id = 'inventory_db'
    database = instance.database(database_id)
    database.run_in_transaction(lambda transaction: transaction.execute_update(dml_statement))

def query_data(select_statement):
    spanner_client = spanner.Client()
    instance_id = 'inventory'
    instance = spanner_client.instance(instance_id)
    database_id = 'inventory_db'
    database = instance.database(database_id)
    
    with database.snapshot() as snapshot:
        result_set = snapshot.execute_sql(select_statement)
        rows = list(result_set)
        metadata = result_set.metadata
    
    return rows, metadata

def get_ledger_data(order_id):
    select_statement = f"SELECT fulfillment_status FROM 'InventoryLedger' WHERE order_id = {order_id}"
    results = query_data(select_statement)
    if results:
        return results[0]
    else:
        return None
    
def get_ship_location(delivery):
    select_statement = f"SELECT id FROM 'InventoryLocations' WHERE fulfillment_type = {delivery}"
    results = query_data(select_statement)
    if results:
        return results[0]
    else:
        return None
    
def update_disp_donum(sku, quantity):
    disp_statement = f'UPDATE "InventoryDisp" WHERE sku = {sku} SET bottles_donum = bottles_donum - {quantity}'
    upload_data(disp_statement)
    
def update_disp_copperpeak(sku, quantity):
    disp_statement = f'UPDATE "InventoryDisp" WHERE sku = {sku} SET bottles_copperpeak = bottles_copperpeak - {quantity}'
    upload_data(disp_statement)
    
def update_disp_groskopf(sku, quantity):
    disp_statement = f'UPDATE "InventoryDisp" WHERE sku = {sku} SET bottles_groskopf = bottles_groskopf - {quantity}'
    upload_data(disp_statement)