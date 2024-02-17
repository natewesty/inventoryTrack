Different end points for orders:

Purchase and decriment
	- Immediate Inven / Disp / Inven Ledg update
Purchase and await pickup
	- Immediate Inven / Inven Ledg update + Fulfill tripped Inven / Disp / Inven Ledg update
Purchase and ship
	- Immediate Inven / Inven Ledg update + Fulfill tripped Inven / Disp / Inven Ledg update
Unfulfilled Refund
	- Immediate Inven / Inven Ledge update
Fulfilled Refund 
	- Break
Exchange
	- Immediate Inven / Inven Ledge / Disp update x 2
Pickup to Ship
	- Immediate Inven / Inven Ledge update x 2 + Fulfill tripped Inven / Disp / Inven Ledge update


Functional script needs:

Physical Movement - updates Inventory, InventoryLedger & InventoryDisp as fulfilled

Sell & Sleep - updates Inventory & Inventory Disp and awaits fulfillment trigger

*******************************************************************************

Completed Items:

- Build "Listening" API structure to capture webhooks
- Write functional logic for processing Orders
- Write function logic for processing Products (includes Inventory bulk moves)
- Create and build out active server location to maintain run

Still Needs to be Done:

- Build UI for user interaction
- Final refactor and documentation passthrough
- Test webhook capture / logistical processising functionality (Post functionality OFF)
- Push to PROD

*******************************************************************************

docker build -t gcr.io/inventory-project-412117/inventorytrack .
docker push gcr.io/inventory-project-412117/inventorytrack
gcloud run deploy gcr.io/inventory-project-412117/inventorytrack

