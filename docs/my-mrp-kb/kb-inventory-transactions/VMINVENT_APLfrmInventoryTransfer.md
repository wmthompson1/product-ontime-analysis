Transferring Inventory Between Locations




# Transferring Inventory Between Locations

In some instances, it may be necessary to transfer
inventory from one warehouse location to another. For example, you
may receive parts into a holding location for inspection before making
the parts available to the plant. After you inspect a number of these
parts, you can transfer them to an available inventory location. Or,
when parts fail inspection, you might quarantine them by transferring
them to a different location that is named and coded as unavailable
inventory.

If you are licensed to use multiple sites, you can transfer inventory
between warehouses in the same site only.

To transfer inventory between locations:

1. Select Inventory,
   Inventory Transaction Entry.
2. Select Edit, Transfer
   Inventory Between Locations.
3. If you are licensed
   to use multiple sites, click the Site ID arrow and select a site
   to use. If you are licensed to use a single site, this field is
   unavailable.
4. In the Part field, specify
   the part to transfer. You can browse for a part either by ID or
   by description.
5. Specify the quantity
   to transfer. For standard parts, specify the quantity to transfer
   in the Quantity field. Depending on your preferences settings,
   the quantity on hand in the parts default warehouse location
   may be inserted by default. You can specify a different value.
   See [Using
   the Primary Warehouse and Location as the Default From Location](Using_the_Primary_Warehouse_and_Location_as_the_Default_From_Location.md).

If you are transferring a piece-tracked
part, specify the number of pieces and the required dimensions. To
view the dimensions of pieces in your inventory, click Inventory Pieces.

6. In the Reason field,
   specify the reason you are transferring the material. This field
   may be required depending on the settings in Site Maintenance.
   When you transfer materials between warehouses, adjustment transactions
   are made. The Site Maintenance settings that apply to inventory
   adjustments also apply to transfers. See [Specifying
   Information on the Defaults Tab](Specifying_Information_on_the_Defaults_Tab_site.md).
7. In the From fields,
   specify the warehouse location from which you are transferring
   the part. Depending on your preferences settings, the parts primary
   warehouse and location may be inserted by default. You can specify
   a different value. See [Using
   the Primary Warehouse and Location as the Default From Location](Using_the_Primary_Warehouse_and_Location_as_the_Default_From_Location.md).

If you use [dimensional
reporting](Dimension_Reporting.md), the default dimension IDs for the debit transaction
are inserted into the Dimension 1 and Dimension 2 fields. The priorities
you established for debit transactions for Adjustments are used to
determine which IDs are inserted into the fields. Click the browse
button to override the default dimension ID used for the debit transaction.
If you use dimensional reporting and track costs by customer order
ID, specify the ID of the order to associated with this transaction
in the Customer Order ID field.

6. In the To fields, specify
   the warehouse location to which you are transferring the part.

If you use [dimensional
reporting](Dimension_Reporting.md), the default dimension IDs for the debit transaction
are inserted into the Dimension 1 and Dimension 2 fields. The priorities
you established for debit transactions for Adjustments are used to
determine which IDs are inserted into the fields. Click the browse
button to override the default dimension ID used for the debit transaction.
If you use dimensional reporting and track costs by customer order
ID, specify the ID of the order to associated with this transaction
in the Customer Order ID field.

6. Click Save.

The transfer creates an Adjust Out transaction
for the From location, and a matching Adjust In transaction for the
To location.

[![btn_mini.gif](btn_mini.gif "btn_mini.gif")](User_defined_Help_Files_Inventory_Transaction_Entry.md) User-defined Help