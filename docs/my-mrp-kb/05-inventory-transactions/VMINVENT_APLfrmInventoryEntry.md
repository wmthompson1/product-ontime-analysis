Using Inventory Transaction Entry




# Using Inventory Transaction Entry

Use Inventory Transaction Entry for six basic operations:

* Receipt of a fabricated
  material into inventory. You can receive inventory [by
  work order](Receiving_Materials_Into_Inventory.md) or [by part](Receiving_by_Part.md).
* [Issue
  Material to a work order.](VMINVENTfrmIssue.md)
* [Adjust
  material into inventory (add material to inventory).](Adjusting_Materials.md)
* [Receipt
  return (returns a material to the work order)](Returning_Received_Materials.md).
* [Issue
  return (return an issued material to the stockroom)](Returning_Issued_Materials.md).
* [Adjust
  material out of inventory (subtracts from inventory)](Adjusting_Materials.md).

All of these operations are performed using the same general procedure
with only slight variations.

If you are licensed to use multiple sites, enter inventory transactions
on a site-by-site basis.

You can also view consignment inventory transactions. You cannot
create consignment inventory transaction in the Inventory Transaction
Window. You must use the Consignment features to create consignment
inventory transactions.

## Fields

The Inventory Transaction window contains these fields:

Site
ID - The ID of the site where the transaction takes place.
If you are licensed to use a single site, this field is unavailable.

Transaction
ID - The ID of the transaction. This ID is generated when you
save a transaction.

Transaction Date - The date of the transaction.

Work Order Base ID - The base ID of the work order.
This field is available if you are performing a Receipt by Work Order,
Issue, Receipt Return, or Issue Return transaction.

Lot ID - The lot ID of the work order. This field
is available if you are performing a Receipt by Work Order, Issue,
Receipt Return, or Issue Return transaction.

Split ID - If the work order has been split, the
split ID of the work order. This field is available if you are performing
a Receipt by Work Order, Issue, Receipt Return, or Issue Return transaction.

Sub ID - If
the work order has a leg, the ID of the leg. This field is available
if you are performing an Issue or Issue Return transaction.

Oper # - The ID of the operation that requires
a material. This field is available if you are performing an Issue
or Issue Return transaction.

Piece
No - The ID of the material card. This field is available if
you are performing an Issue or Issue Return transaction.

New
Material Req't - Indicates that the material requirement is
new. Use this check box to add new material requirements when you
issue materials to work orders. This check box is available for the
SYSADM user only.

Part ID - The ID of
the part in the transaction. You can specify a part ID if you are
performing an Issue of a new material requirement, Adjust In, Receipt
by Part, and Adjust Out. The field is populated for you if you are
performing a Receipt by Work Order, Issue of an existing material
requirement, Receipt Return, or Issue Return.

User ID - The ID of
the user who entered the transaction.

Employee
ID - The ID of the employee who worked on the labor ticket.
This field is available only if you select the Autogen Labor During
Receipt check box in Site Maintenance. See [Specifying
Information on the Defaults Tab](Specifying_Information_on_the_Defaults_Tab_site.md).

Required
- The quantity required on the material requirement card. A value
is displayed in this field for Issue and Issue Return transactions
only.

Issued
- The quantity previously issued to the material requirement. A value
is displayed in this field for Issue and Issue Return transactions
only.

Desired - The quantity desired on the
work order. A value is displayed in this field for Receipt by Work
Order, Receipt by Part, and Receipt Return transactions.

Received
- The quantity previously received on the work order. A value is displayed
in this field for Receipt by Work Order, Receipt by Part, and Receipt
Return transactions.

Due - The quantity remaining to be issued or received.
For issues and issue returns, this value is the Required quantity
minus the Issued quantity. For Receipt by Work Order and Receipt Return
transactions, this value is the Desired quantity minus the Received
quantity.

On
Hand - The total quantity of the part on hand in your warehouse
locations. This includes available, on-hold, and unavailable quantities.

Available
- The total available quantity in your warehouses locations.

Pcs
- For dimensional inventory, the number or pieces required for a material
issue. A value is displayed in this field for Issues and Issue Returns.

Length/Width/Height
- For dimensional inventory material requirements, the dimensions
of the required pieces. Values are displayed in these fields for Issues
and Issue Returns. Values are displayed depending on which dimensions
are required for the piece. See [Setting
Up Piece Tracked Parts in Part Maintenance](Setting_Up_Piece_Tracked_Parts_in_Part_Maintenance.md).

Transaction Class - The type of inventory transaction.

Quantity
- The quantity of part in the transactions.

Pcs
- For dimensional inventory, the number of pieces in the transaction.

Length/Width/Height - For dimensional inventory,
the dimensions of the pieces in the transaction.

Warehouse
- The warehouse associated with the transactions.

Location
- The location where the parts are received or issued.

Issue Reason - For issue transactions and issue
return transactions, the reason for the transaction. Specify whether
a reason code is required in Site Maintenance.

Description
- A description of the transaction.

Material
- The material cost of the part.

Labor - The cost
of labor incurred during the manufacture of the part.

Burden - The overhead
cost incurred for the part.

Service
- The service cost incurred during the manufacture of the part.

Fixed
- The fixed cost incurred for the part.

Reason - For adjust in and adjust out
transactions, the reason for the adjustment.

Account ID
- For adjust in and adjust out transaction, the account ID used to
record the transaction cost.

User Dimension 1 and 2 - For adjust in and adjust
out transactions, the user dimensions associated with the transaction.
See [Creating Dimension
IDs](Creating_Dimension_IDs.md).

Customer Order ID - If you use dimensional reporting
and track costs by customer ID, the customer order ID associated with
the adjustment. See [Dimension
Reporting](Dimension_Reporting.md).

Work Order Table
- For receipt by part transactions, a list of work orders for the
part.

WBS Code - The WBS code associated with
the transaction. This field is available only if you are licensed
to use Projects A&D functions and are performing an adjust-in
transaction.

Proj
Ref Seq No - The project reference sequence number associated
with the transaction. This field is available only if you are licensed
to use Projects A&D functions and are performing an adjust-in
transaction.

Sub
ID - The sub ID of the project associated with the transaction.
This field is available only if you are licensed to use Projects A&D
functions and are performing an adjust-in transaction.

Department
ID - The department to charge for the transaction. This field
is available only if you are licensed to use Projects A&D functions
and are performing an adjust-in transaction.

[![btn_mini.gif](btn_mini.gif "btn_mini.gif")](User_defined_Help_Files_Inventory_Transaction_Entry.md) User-defined Help