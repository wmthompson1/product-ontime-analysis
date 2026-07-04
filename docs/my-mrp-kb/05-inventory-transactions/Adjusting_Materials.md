Adjusting Materials




# Adjusting Materials

Use the Adjust/In or Adjust/Out options to synchronize
VISUAL inventory quantities with your physical inventory.

To adjust inventory:

1. Select Inventory,
   Inventory Transaction Entry.
2. If you are licensed
   to use multiple sites, click the Site ID
   arrow and select the site whose inventory you are adjusting.
3. To add items to the
   inventory, select the Adjust In option.

To remove items from inventory, select the
Adjust Out option.

4. In the Part ID field,
   specify the part to adjust in or out.
5. Specify the quantity
   of materials you are adjusting and the location where you are
   adjusting them. Specify this information:

Quantity Specify
the quantity to adjust in or out. To add one item to the inventory,
enter one in the quantity field. DO NOT enter the total inventory
count. For example, VISUAL inventory shows 15 in stock but you actually
have 16 for the location count: Adjust/In a quantity of 1.

Warehouse Specify
the ID of the warehouse receiving the material adjustment.

Location Specify
the ID of the location receiving the adjustment. To view a list of
locations that can store the part, click the Location browse button.

6. For Adjust/In transactions,
   specify the costs of the materials you are adjusting in. To use
   the [costs defined on the
   part record](VMPRTMNTfrmPart.md#Costing), leave these fields blank. To override the costs,
   specify the Material, Labor, Burden, and Service costs for the
   new inventory. Take care not to specify zero. If you specify zero,
   then when this material is applied to the cost of a later work
   order or customer order the zero cost is passed on to cost of
   goods sold.
7. For Adjust/In transactions,
   specify whether to include the purchase burden amount specified
   on the Part Maintenance record. To include purchase burdens, select
   Options, Apply Purchase Burdens until a check box is placed next
   to the menu option. To exclude purchase burdens, select Options,
   Apply Purchase Burdens until the check box is removed from the
   menu option.
8. In the Adjustments section,
   specify this information:

Reason Specify
the reason for the adjustment. Depending on [your
settings in Site Maintenance](Specifying_Information_on_the_Defaults_Tab_site.md), this field may be required.

Account ID Specify
the account to use to record the costs of this adjustment. To use
the default account specified in the [sites
general ledger interface](Using_the_G_L_Account_Interface_Table.md), leave this field blank.

9. If you use [dimensional
   reporting](Dimension_Reporting.md), the default dimension IDs for the debit transaction
   are inserted into the Dimension 1 and Dimension 2 fields. The
   priorities you established for debit transactions for Adjustments
   are used to determine which IDs are inserted into the fields.
   Click the browse button to override the default dimension ID used
   for the debit transaction.
10. If you use dimensional
    reporting and track costs by customer order ID, specify the ID
    of the order to associated with this transaction.
11. Click Save.
    A transaction ID is generated.

## For Project and A&D Users

If you select the Adjust/In
option, the Adjust/In Project Information section is displayed at
the bottom of the window.

When you specify a project warehouse, the Project Information section
is populated with the default WBS Code, Project Reference Sequence
Number, and Sub ID for the project. The department ID associated with
the default WBS code is also inserted. You can specify different information.

[![btn_mini.gif](btn_mini.gif "btn_mini.gif")](User_defined_Help_Files_Inventory_Transaction_Entry.md) User-defined Help