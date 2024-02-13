import os, schedule, time
from datetime import datetime
from google.cloud import spanner

def upload_data(dml_statement, params=None):
    spanner_client = spanner.Client()
    instance_id = 'inventory'
    instance = spanner_client.instance(instance_id)
    database_id = 'inventory_db'
    database = instance.database(database_id)
    
    # Define param_types based on params
    param_types = {}
    param_mapping = {}
    if params is not None:
        for i, (key, value) in enumerate(params.items()):
            param_name = f'p{i+1}'
            param_mapping[param_name] = value
            if isinstance(value, str):
                param_types[param_name] = spanner.param_types.STRING
            elif isinstance(value, int):
                param_types[param_name] = spanner.param_types.INT64
            elif isinstance(value, float):
                param_types[param_name] = spanner.param_types.FLOAT64
            elif isinstance(value, datetime):
                param_types[param_name] = spanner.param_types.TIMESTAMP
            # Add more types as needed

    # Replace original param names with 'p1', 'p2', etc. in the DML statement
    for original, replacement in param_mapping.items():
        dml_statement = dml_statement.replace(f'@{original}', f'@{replacement}')

    database.run_in_transaction(lambda transaction: transaction.execute_update(dml_statement, params=param_mapping, param_types=param_types))

def query_data(select_statement, params=None):
    spanner_client = spanner.Client()
    instance_id = 'inventory'
    instance = spanner_client.instance(instance_id)
    database_id = 'inventory_db'
    database = instance.database(database_id)
    
    with database.snapshot() as snapshot:
        result_set = snapshot.execute_sql(select_statement, params=params)
        rows = list(result_set)
        metadata = result_set.metadata
    
    return rows, metadata

def get_ledger_data(order_id):
    select_statement = "SELECT fulfillment_status FROM 'InventoryLedger' WHERE order_id = @order_id"
    results = query_data(select_statement, params={"order_id": order_id})
    if results:
        return results[0]
    else:
        return None

def get_ship_location(delivery):
    select_statement = "SELECT id FROM 'InventoryLocations' WHERE fulfillment_type = @delivery"
    results = query_data(select_statement, params={"delivery": delivery})
    if results:
        return results[0]
    else:
        return None

def update_disp_donum(sku, quantity):
    disp_statement = 'UPDATE "InventoryDisp" SET bottles_donum = bottles_donum - @quantity WHERE sku = @sku'
    upload_data(disp_statement, params={"sku": sku, "quantity": quantity})

def update_disp_copperpeak(sku, quantity):
    disp_statement = 'UPDATE "InventoryDisp" SET bottles_copperpeak = bottles_copperpeak - @quantity WHERE sku = @sku'
    upload_data(disp_statement, params={"sku": sku, "quantity": quantity})

def update_disp_groskopf(sku, quantity):
    disp_statement = 'UPDATE "InventoryDisp" SET bottles_groskopf = bottles_groskopf - @quantity WHERE sku = @sku'
    upload_data(disp_statement, params={"sku": sku, "quantity": quantity})

def schedule_transfer(sku, from_location, to_location, transfer_date, quantity):
    ledger_statement = 'INSERT INTO "TransferLedger" (sku, from_location, to_location, transfer_date, quantity, status) VALUES (@sku, @from_location, @to_location, @transfer_date, @quantity, "pending")'
    upload_data(ledger_statement, params={"sku": sku, "from_location": from_location, "to_location": to_location, "transfer_date": transfer_date, "quantity": quantity})
    
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
        disp_statement = 'UPDATE "InventoryDisp" SET bottles_donum = bottles_donum + @quantity WHERE sku = @sku'
    elif to_location == 'Copper Peak':
        disp_statement = 'UPDATE "InventoryDisp" SET bottles_copperpeak = bottles_copperpeak + @quantity WHERE sku = @sku'
    elif to_location == 'Groskopf':
        disp_statement = 'UPDATE "InventoryDisp" SET bottles_groskopf = bottles_groskopf + @quantity WHERE sku = @sku'

    upload_data(disp_statement, params={"sku": sku, "quantity": quantity})

    # Record the transfer in the InventoryLedger
    ledger_statement = 'INSERT INTO "TransferLedger" (sku, from_location, to_location, transfer_date, quantity) VALUES (@sku, @from_location, @to_location, @transfer_date, @quantity)'
    upload_data(ledger_statement, params={"sku": sku, "from_location": from_location, "to_location": to_location, "transfer_date": transfer_date, "quantity": quantity})

def process_transfer(transfer):
    # Process the transfer if the date is on or before the current date
    sku, from_location, to_location, transfer_date, quantity, status = transfer
    if transfer_date <= datetime.today():
        transfer_inventory(sku, from_location, to_location, transfer_date, quantity)

        # Update the transfer status
        update_statement = 'UPDATE "TransferLedger" SET status = "processed" WHERE sku = @sku AND from_location = @from_location AND to_location = @to_location AND transfer_date = @transfer_date AND quantity = @quantity'
        upload_data(update_statement, params={"sku": sku, "from_location": from_location, "to_location": to_location, "transfer_date": transfer_date, "quantity": quantity})

def checkrun_transfers():
    # Get all pending transfers that are due to be processed
    select_statement = 'SELECT * FROM "TransferLedger" WHERE status = "pending" AND transfer_date <= @today'
    transfers, _ = query_data(select_statement, params={"today": datetime.today().strftime("%Y-%m-%d")})

    for transfer in transfers:
        # Process the transfer
        sku, from_location, to_location, transfer_date, quantity, status = transfer
        transfer_inventory(sku, from_location, to_location, transfer_date, quantity)

        # Update the transfer status
        update_statement = 'UPDATE "TransferLedger" SET status = "processed" WHERE sku = @sku AND from_location = @from_location AND to_location = @to_location AND transfer_date = @transfer_date AND quantity = @quantity'
        upload_data(update_statement, params={"sku": sku, "from_location": from_location, "to_location": to_location, "transfer_date": transfer_date, "quantity": quantity})