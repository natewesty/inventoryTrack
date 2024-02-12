import os, schedule, time
from datetime import datetime
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
    
def schedule_transfer(sku, from_location, to_location, transfer_date, quantity):
    # Record the transfer in the InventoryLedger
    ledger_statement = f'INSERT INTO "TransferLedger" (sku, from_location, to_location, transfer_date, quantity, status) VALUES ({sku}, {from_location}, {to_location}, {transfer_date}, {quantity}, "pending")'
    upload_data(ledger_statement)
    
def transfer_inventory(sku, from_location, to_location, transfer_date, quantity):
    # Update the inventory at the from_location
    if from_location == 'Donum':
        update_disp_donum(sku, quantity)
    elif from_location == 'Copper Peak':
        update_disp_copperpeak(sku, quantity)
    elif from_location == 'Groskopf':
        update_disp_groskopf(sku, quantity)

    # Update the inventory at the to_location
    if to_location == 'Donum':
        disp_statement = f'UPDATE "InventoryDisp" WHERE sku = {sku} SET bottles_donum = bottles_donum + {quantity}'
    elif to_location == 'Copper Peak':
        disp_statement = f'UPDATE "InventoryDisp" WHERE sku = {sku} SET bottles_copperpeak = bottles_copperpeak + {quantity}'
    elif to_location == 'Groskopf':
        disp_statement = f'UPDATE "InventoryDisp" WHERE sku = {sku} SET bottles_groskopf = bottles_groskopf + {quantity}'

    upload_data(disp_statement)

    # Record the transfer in the InventoryLedger
    ledger_statement = f'INSERT INTO "TransferLedger" (sku, from_location, to_location, transfer_date, quantity) VALUES ({sku}, {from_location}, {to_location}, {transfer_date}, {quantity})'
    upload_data(ledger_statement)
    
def process_transfer(transfer):
    # Process the transfer if the date is on or before the current date
    sku, from_location, to_location, transfer_date, quantity, status = transfer
    if transfer_date <= datetime.today():
        transfer_inventory(sku, from_location, to_location, transfer_date, quantity)

        # Update the transfer status
        update_statement = f'UPDATE "TransferLedger" SET status = "processed" WHERE sku = {sku} AND from_location = {from_location} AND to_location = {to_location} AND transfer_date = {transfer_date} AND quantity = {quantity}'
        upload_data(update_statement)
    
def checkrun_transfers():
    # Get all pending transfers that are due to be processed
    select_statement = f'SELECT * FROM "TransferLedger" WHERE status = "pending" AND transfer_date <= "{datetime.today().strftime("%Y-%m-%d")}"'
    transfers, _ = query_data(select_statement)

    for transfer in transfers:
        # Process the transfer
        sku, from_location, to_location, transfer_date, quantity, status = transfer
        transfer_inventory(sku, from_location, to_location, transfer_date, quantity)

        # Update the transfer status
        update_statement = f'UPDATE "TransferLedger" SET status = "processed" WHERE sku = {sku} AND from_location = {from_location} AND to_location = {to_location} AND transfer_date = {transfer_date} AND quantity = {quantity}'
        upload_data(update_statement)

def start_scheduler():
    # Run the checkrun_transfers function every hour
    schedule.every(1).hours.do(checkrun_transfers)

    while True:
        schedule.run_pending()
        time.sleep(1)
        