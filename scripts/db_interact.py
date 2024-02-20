import os, schedule, time
from datetime import datetime
import logging
import json
import sqlalchemy
from sqlalchemy import text
from google.cloud.sql.connector import Connector, IPTypes

# Configure logging
logging.basicConfig(filename='db_interact.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def connect_with_connector() -> sqlalchemy.engine.base.Engine:
    instance_connection_name = 'inventory-project-412117:us-west1:inventory'
    db_user = 'cloud_worker'
    db_pass = 'Ux2_Y:)yssA{lA^N'
    db_name = 'inventory_db'
    
    ip_type = IPTypes.PUBLIC
    
    # Create a Connector object
    connector = Connector(ip_type)

    def getconn() -> sqlalchemy.engine.base.Connection:
        conn = connector.connect(
            instance_connection_name,
            "pg8000",
            user=db_user,
            password=db_pass,
            db=db_name
        )
        return conn

    pool = sqlalchemy.create_engine(
        "postgresql+pg8000://",
        creator=getconn,
    )
    return pool

# Create a connection engine
engine = connect_with_connector()

def upload_data(dml_statement, params=None):
    try:
        # Begin a transaction
        with engine.begin() as connection:
            # Execute the DML statement
            result = connection.execute(dml_statement, params)
            logging.info(f"{result.rowcount} record(s) updated.")
                
            return result.rowcount > 0  # Return True if data was written, False otherwise
    except Exception as e:
        logging.error(f"Unexpected error executing DML statement: {e}")
    return False  # Return False if an error occurred


def query_data(select_statement, params=None):
    try:
        with engine.connect() as connection:
            result = connection.execute(sqlalchemy.text(select_statement), params)
            rows = result.fetchall()
        return rows
    except Exception as e:
        logging.error(f"Error executing SELECT statement: {e}")
        return None

def get_ledger_data(order_id):
    try:
        select_statement = text('SELECT fulfillment_status FROM "InventoryLedger" WHERE order_id = :order_id')
        results = query_data(select_statement, params={"order_id": order_id})
        if results:
            return results[0][0]  # Assuming fulfillment_status is the first column
        else:
            return None
    except Exception as e:
        logging.error(f"Error getting ledger data: {e}")
        return None

def get_ship_location(delivery):
    try:
        select_statement = text('SELECT name FROM "InventoryLocations" WHERE fulfillment_type = :delivery')
        results = query_data(select_statement, params={"fulfillment_type": delivery})
        if results:
            return results[0][0]  # Assuming id is the first column
        else:
            return None
    except Exception as e:
        logging.error(f"Error getting ship location: {e}")
        return None

def update_disp(sku, quantity, location): ### PENDING REMOVAL AND REPLACEMENT VIA DATA_PROCESSING ###
    try:
        disp_statement = text(f'UPDATE "InventoryDisp" SET {location} = {location} - :quantity WHERE sku = :sku')
        upload_data(disp_statement, params={"quantity": quantity, "sku": sku})
    except Exception as e:
        logging.error(f"Error updating disp: {e}")

# Define the location aliases
location_aliases = {
    'Donum': 'bottles_donum',
    'Copper Peak': 'bottles_copperpeak',
    'Groskopf': 'bottles_groskopf',
    # Add more aliases as needed
}

def transfer_inventory(sku, from_location, to_location, quantity):
    try:
        # Convert the locations to their aliases
        from_location_alias = location_aliases.get(from_location, from_location)
        to_location_alias = location_aliases.get(to_location, to_location)
        
        # Update the inventory at the from_location
        update_disp(sku, quantity, from_location_alias)
        
        # Update the inventory at the to_location
        update_disp(sku, -quantity, to_location_alias)
        
        # Record the transfer in the InventoryLedger
        ledger_statement = text('INSERT INTO "TransferLedger" (sku, from_location, to_location, quantity) VALUES (:sku, :from_location, :to_location, :quantity);')
        upload_data(ledger_statement, params={"sku": sku, "from_location": from_location_alias, "to_location": to_location_alias, "quantity": quantity})
    except Exception as e:
        logging.error(f"Error transferring inventory: {e}")

