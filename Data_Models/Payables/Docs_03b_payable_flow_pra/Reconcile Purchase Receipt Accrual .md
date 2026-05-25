# KB0731106

## How to reconcile Purchase Receipt Accrual to Ledger.

### Key point
In Ledger > Accounting Window, pull up the PRA account.  Drill into the period and ensure the only Type batches are API (Payable Invoices) and PUR (Purchase Journal).  If Projects is in use, there will also be PRJ (Project) batches.  If there are other batch types, these should be reversed using a General Journal Entry.  Refer to related KB0732063 for additional details on obtaining a GJ total.

**Resolution** :
While end to end reconciliation of accounts is outside the scope of what support can provide, the following guidelines can be used to perform the reconciliation.  Should specific data issues be identified in the course of reconciling, support can provide assistance/direction to help get those specific data items corrected. 

Additional assistance can be provided as a billable service.  Requests for a quote can be placed by selecting 'Create Consulting Request' from the case or Infor Concierge > Create Consulting Request. 

Before beginning, ensure all transactions are entered and posted.

Purchase Receipt Accrual (PRA) reconciliation uses 3 reports:

Ledger > Post Manufacturing Journals > Reports > PO Accrual report:  Lists all Uninvoiced Receivers.
Admin > Costing Tools > File > P/O Accrual Analysis:  Compares Receivers to Invoices.
Payables > Invoice Entry > File > Print Uninvoiced Receipts:  Lists all Uninvoiced Receivers.

Print the PO Accrual Report.  This should match to the balance in the Accounting Window for the PRA account.  If it does not, follow these steps:

1.  In Ledger > Accounting Window, pull up the PRA account.  Drill into the period and ensure the only Type batches are API (Payable Invoices) and PUR (Purchase Journal).  If Projects is in use, there will also be PRJ (Project) batches.  If there are other batch types, these should be reversed using a General Journal Entry.  Refer to related KB0732063 for additional details on obtaining a GJ total.

2.  Verify that there are no 0.00 batches.  These batches may not have posted correctly due to changing screens or other disturbances while posting and would create a batch for zero dollars.  To find $0 batches, go to Ledger > General Journal Entry > Edit > View Batch Information and browse batch ID's by posting date.  If the amount is $0.00, pull them into the window.  If there are no details to the batch, the batch needs to be deleted and reposted. Reference related KB1015071. 

3.  If any prepayments were entered, verify that the PRA account was not entered on the payable line.  Reference related KB0732848.

4.  Print the PO Accrual Analysis report.  Select ‘Incorrectly Matched Amounts Only’. Look for recent POs where the invoice column is not the same as the receiver column. Ignore any return receivers (negative value). These may be different and the variance is posted to Purchase Return Expense account found in the G/L Interface table.

If there are any exceptions, identify the part.  Go to Admin > Costing Tools > Options > Recalculate Distributions.  Enter the part as the Starting and Ending Part ID.  Check ‘Reset P/O Receipts from Matched Invoices' and click Start.

If there is no part on the purchase order select Recalculate all Distributions Including Non-part Transactions and enter the date of the purchase order in the Process Transactions on or After date field.

5. Force the transaction through Costing Tools:

Cost to Check = Purchases. 
Enter the purchase order as Starting and Ending Order ID. 
Uncheck the Exceptions Only box. 
Click the ‘Run’ icon. 
Highlight the row returned. 
Click the ‘Set Posting Candidate’ icon. 
Click the ‘Journal Preparation’ icon. 
Go to Ledger/Post Manufacturing Journals and post the Purchase Journal.
6.  Any transactions that are not posted because of an error in the date can be found by running the following SQL statements:

SELECT * FROM PURCHASE_DIST WHERE POSTING_STATUS = 'U'
SELECT * FROM PAYABLE_DIST WHERE POSTING_STATUS = 'U'

Any future dated transaction would not cause a problem. 

7.  Any transactions that debit the PRA account but does not reference a receiver can found by running the following SQL statement.  Replace the variable with the PRA account:

SELECT * FROM PAYABLE_LINE WHERE GL_ACCOUNT_ID = 'ENTER PO ACCRUAL ACCOUNT HERE' AND RECEIVER_ID IS NULL

If the above steps do not identify the issue, in a fully costed, static environment:

Payables > Invoice Entry > File > Print Uninvoiced Receipts Detail
Remove Starting Date
Check boxes for Status:
 Released
 Closed
 Cancelled

Should match:

Admin > Costing Tools > File > Print P/O Accrual Analysis Report
 Received, Not Invoiced Only


 


Note :
Purchase Receipts Costing

The receiver values are determined by the Costing Method in Admin > Accounting Entity Maintenance in the Costing Tab.

•Standard Costing:  The receipt is valued in inventory using the value in Part Maintenance.  A Purchase Price Variance is created when the invoice is matched to the receiver if there is a price difference.

**Skills uses actual costing**
• Actual or Average Costing w/Source of Raw Material Cost set to ‘Purchase Order’:  The receipt is valued at the PO price and a variance is created when the invoice is matched to the receiver if there is a price difference.

• Actual or Average Costing w/Source of Raw Material Cost set to ‘A/P Invoices’:  The receipt is valued at PO Price until the Invoice is matched to the receiver.  If there is a price difference, an adjustment to inventory is made and all issues (to Work Orders and Shipments) are updated to reflect the true actual cost.

 



