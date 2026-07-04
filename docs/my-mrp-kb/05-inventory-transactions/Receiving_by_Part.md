Receiving by Part




# Receiving by Part

If you work in a repetitive manufacturing industry
and issue several work orders for the same part, you may find it more
appropriate to receive by part ID instead of by the individual work
orders used to manufacture the parts.

When you click Receipt by Part, a list of release work orders for
the part is displayed. When you specify a quantity to receive, the
quantity is automatically distributed to the open orders starting
with the work order with the earliest Desired Want Date. If the Receipt
Qty plus Work order Received Qty plus any Allocated Qty (for linked
customer orders) is greater than the first work orders Desired Qty,
the remaining quantity is distributed to the next oldest work order.
You can override the calculated quantities.

If you specify a quantity greater than the quantity due for released
work orders, you can apply the excess inventory to firmed work orders
or closed work orders.

To receive inventory by part:

1. Select Inventory,
   Inventory Transaction Entry.
2. If you are licensed
   to use multiple sites, click the Site ID arrow and select the
   site for the transaction. If you are licensed to use a single
   site, this field is unavailable.
3. Click Receipt
   by Part.
4. In the Part ID field,
   specify the part to receive. The total quantity desired, received,
   and due for all released jobs are inserted into the appropriate
   fields. A list of released work orders for the manufacture of
   the Part ID is displayed in the Job ID table. The work orders
   are listed in order of the most recent Desired Want Date. To view
   all of the work orders for this part regardless of their status,
   select Options, View
   All Work Orders.
5. Specify the quantity
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

4. In the work order table,
   the quantity you specified is assigned to open orders. To adjust
   the quantity received to an order, specify a new value in the
   ReceiptQty field. The total amount remaining to be applied to
   an order is displayed above the table.
5. Click Save.