Issuing Materials to Work Orders




# Issuing Materials to Work Orders

Use Inventory Transaction Entry to issue materials
your inventory to a work order material requirement. Use this function
to issue materials to requirements that are not linked to purchase
orders.

For requirements linked to purchase orders, use Purchase Receipt
Entry to create inventory transactions. When you receive a linked
purchase order, two inventory transactions are created. A receipt
transaction is created to receive the quantity into inventory. An
issue transaction to the requirement is then created.

When you issue materials through a manual issue transaction or through
a purchase receipt, the material requirement completion percentage
is updated in the Manufacturing Window. If you receive the total required
quantity, the material requirement is closed.

Use the Issue function in the main Inventory Transaction window
to issue a particular part to a single requirement. To issue parts
to all requirements, use the Issue By Exception feature. See [Using
Issue By Exception](VMINVENT_APLfrmIssue.md).

To issue parts to a material requirement:

1. Select Inventory,
   Inventory Transaction Entry.
2. If you are licensed
   to use multiple sites, click the Site ID
   arrow and select the site for the transaction. If you are licensed
   to use a single site, this field is unavailable.
3. Click Issue.
4. Click the Work Order
   ID browse button and select the Work Order to which to issue materials.
5. Click the Piece No browse
   button and select the material requirement. After you select a
   piece number, the Part ID is displayed. In the Quantities section,
   the total quantity required, the quantity previously issued to
   the requirement, and the remaining quantity due to be issued are
   displayed. In addition, the current quantity of the part on hand
   and the current quantity available are displayed.

| POSTIT.gifstyle="width: | If you are the SYSADM user, you can add a requirement directly in Inventory Transaction. You must have the NewMaterialMode entry in the InventoryEntry section of Preferences Maintenance set to On to add new material requirements in the Inventory Transaction Entry window. To add a requirement, specify a piece number that does not exist as a material requirement on the work order. Select the New Material Reqd check box and use the Part ID browse button to select the part to add. |

6. Specify the quantity
   of materials you are issuing and the location from which to issue
   them. Specify this information:

Quantity Specify
the quantity to issue.

Warehouse Specify
the ID of the warehouse issuing the materials.

Location Specify
the ID of the location issuing the materials.

Issue Reason
Specify the code that indicates the reason you are issuing the materials.
Depending on the settings in Site Maintenance, this field may  be
required. See [Specifying
Information on the Defaults Tab](Specifying_Information_on_the_Defaults_Tab_site.md).

Description
Specify a description of the transaction.

7. Click Save.
   A transaction ID is generated.

[![btn_mini.gif](btn_mini.gif "btn_mini.gif")](User_defined_Help_Files_Inventory_Transaction_Entry.md) User-defined Help