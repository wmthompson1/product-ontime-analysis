# SQLMesh Incremental Three‑Way Match Model

William - yes, we can make the Three-Way Match SQLMesh model incremental, and order_date is one candidate, but not the best one.
Let me walk you through the reasoning and then give you the production-ready incremental SQLMesh model.
First: What Should the Incremental Key Be?
In SQLMesh, an incremental model must be driven by a monotonically increasing timestamp that reflects when the business truth changes.
Let’s evaluate the candidates:
1. PURCHASE_ORDER.ORDER_DATE
Not ideal.
Why?
A PO can be created on Monday
Received on Wednesday
Invoiced on Friday
If you increment on ORDER_DATE, you miss the receipt and invoice events.
2. RECEIVER.RECEIVED_DATE
Better, but still incomplete.
Why?
Invoices can arrive after receipts
Vouchers can be created after invoices
Corrections can happen after both
3. PAYABLE.INVOICE_DATE or POSTING_DATE
Also incomplete.
Why?
Receipts can occur after invoice creation (service POs)
Receipts can be corrected
PO changes can occur later
4. The Correct Incremental Key:
This is the true business event timestamp.
It captures:
PO changes
Receipts
Receipt corrections
Invoice creation
Voucher posting
Late invoices
Late receipts
Back-dated events
This is the canonical incremental key for a three-way match model.
SQLMesh Incremental Model (Production-Ready)
Below is the incremental version of the model, using a derived event timestamp that captures any change in the three-way match lifecycle.
You can drop this directly into:
Documentation\my-mrp-kb\three_way_match and
SQLMesh Model: Incremental Three-Way Match
Note: The sql was revised 6/29/2026
Why This Incremental Model Is Correct
Uses a derived event timestamp
Captures any change in:
PO
Receipt
Invoice
Voucher
Incremental by time range
SQLMesh will only process rows where event_ts falls in the incremental window.
Handles late receipts
Handles late invoices
Handles corrections
Handles back-dated events
Handles multi-day matching workflows
This is the canonical incremental pattern for procure-to-pay truth.
If you want next:
The diagram
The narrative section
The ontology mapping
The SPARQL patterns
Just tell me which one you want me to generate.
models/three_way_match.sql
revised 6/29/2026
