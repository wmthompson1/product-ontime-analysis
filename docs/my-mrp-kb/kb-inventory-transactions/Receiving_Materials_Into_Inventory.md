Receiving Materials Into Inventory




# Receiving Materials by Work Order

Use Inventory Transaction Entry to receive material
from a work order into inventory. Use this function to receive finished
goods that are not linked to a customer order.

For work orders linked to customer orders, use Shipping Entry to
create inventory transactions. When you ship a linked customer order,
two inventory transactions are created. A receipt transaction is created
to receive the shipped quantity into inventory. An issue transaction
to the customer order is then created.

When you receive finished goods through a manual receipt transaction
or through a shipment, the work order completion percentage is updated
in the Manufacturing Window. If you receive the total quantity of
the order, the work order is closed.

To receive finished goods into your inventory:

1. Select Inventory,
   Inventory Transaction Entry.
2. If you are licensed
   to use multiple sites, click the Site ID
   arrow and select the site that is receiving materials. If you
   are licensed to use a single site, this field is unavailable.
3. In the Transaction Date
   field, specify the date that you are receiving the materials.
   By default the current date is inserted.
4. Click Receipt
   by WO.
5. Click the Work
   Order ID browse button and select the work order from which
   to receive parts. The browse table shows only released work orders.
   If you are licensed to use multiple sites, the browse table shows
   only released work orders created in the site you selected.

After you select a work order, the Part
ID is displayed. In the Quantities section, the total quantity desired
specified on the work order, the quantity previously received, and
the remaining quantity due to be received are displayed. In addition,
the current quantity of the part on hand and the current quantity
available are displayed.

After you select a work order, you can assign
the work order supply to a demand source. See [Allocating
Released Work Order Quantities to Demand](Allocating_Released_Work_Order_Quantities_to_Demand.md).

6. Specify the quantity
   of finished goods you are receiving and the location in which
   to receive them. Specify this information:

Quantity Specify
the quantity to receive.

Warehouse Specify
the ID of the warehouse receiving the finished goods. If a warehouse
is specified on the work order header, than that warehouse ID is inserted.
If no warehouse is specified on the work order header, then the default
warehouse specified for the part is inserted.

Location Specify
the ID of the location receiving the finished goods. To view a list
of locations that can store the part, click the Location browse button.
Depending on your Part Location on the Fly settings in Site Maintenance,
you may be able to specify a new location for the part. See [Specifying
Information on the General Tab](Specifying_Information_on_the_General_Tab_site.md).

Description
Specify a description of the transaction.

Employee ID
This field is displayed only if you selected the Autogen Labor During
Receipt check box in Site Maintenance. If you autogenerate labor tickets,
specify the ID of the employee who complete the labor for this finished
good. See [Specifying
Information on the Defaults Tab](Specifying_Information_on_the_Defaults_Tab_site.md).

7. Click Save.
   The quantity you specified is received into the location you specified.
   A transaction ID is generated.

[![btn_mini.gif](btn_mini.gif "btn_mini.gif")](User_defined_Help_Files_Inventory_Transaction_Entry.md) User-defined Help

[![btn_mini.gif](btn_mini.gif "btn_mini.gif")](Allocating_Released_Work_Order_Quantities_to_Demand.md) Allocating Released Work Order Quantities
to Demand

[![btn_mini.gif](btn_mini.gif "btn_mini.gif")](Assigning_Released_Work_Order_Receipt_Quantities_to_Demand_Links.md) Assigning Released Work Order Receipt
Quantities to Demand Links