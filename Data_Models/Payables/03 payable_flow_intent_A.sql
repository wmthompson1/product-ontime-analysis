/**********************
Payables Data Model 1

Looking for invoices missing on the visual side of the join.
SQL query to explore payable, receiver, and purchase-order relationships.

File path:
  Documentation/Schema/Data_Models/Payables/

Common pitfalls / repo findings
- `INVOICE_NO` appears in some reports and older queries — authoritative schema uses `INVOICE_ID`.
- Some custom reports map `P.VOUCHER_ID = P.INVOICE_ID` for specific integrations (TMX); treat these as exceptions.

payables_invoice_voucher_flow
- Extract help-file information on `INVOICE_ID` in the Payables perspective from `PAYABLE.INVOICE_ID`
  and `RECEIVER_LINE.INVOICE_ID`.
- Place that information in `Documentation/Schema/Data_Models/Payables/payables_invoice_voucher_flow.md`.
**********************/

WITH payables_invoice_voucher_flow AS (
    SELECT
        po.VENDOR_ID,
        pol.PURC_ORDER_ID,
        pol.LINE_NO,
        rl.RECEIVER_ID,
        po.ORDER_DATE,
        rl.LINE_NO AS RCVR_LINE,
        rl.INVOICE_ID AS RCVR_INVOICE,
        r.RECEIVED_DATE,
        p.VOUCHER_ID,
        -- There can be more than one payable invoice per receiver line, so keep payable invoice
        -- details at line level. See PO examples 186603 and 186675 for this dynamic.
        p.INVOICE_ID AS PAYABLE_INVOICE,
        pol.DESIRED_RECV_DATE,
        pol.COMMODITY_CODE,
        ud.STRING_VAL AS CONTROLLED,
        v.USER_6 AS SUPPLIER_TYPE,
        pol.PART_ID,
        part.PLANNER_USER_ID,
        v.USER_7 AS PRODUCT_TYPE,
        rl.TRANSACTION_ID
    FROM Live.dbo.PURC_ORDER_LINE AS pol
    INNER JOIN Live.dbo.PURCHASE_ORDER AS po
        ON pol.PURC_ORDER_ID = po.ID
    LEFT JOIN Live.dbo.PAYABLE_LINE AS pl
        ON pol.PURC_ORDER_ID = pl.PURC_ORDER_ID
       AND pol.LINE_NO = pl.PURC_ORDER_LINE_NO
    LEFT JOIN Live.dbo.PAYABLE AS p
        ON pl.VOUCHER_ID = p.VOUCHER_ID
    -- Receiver follows receiver line in join order so receiver-line details are retained even
    -- when the receiver header is missing.
    LEFT JOIN Live.dbo.RECEIVER_LINE AS rl
        ON rl.PURC_ORDER_ID = pol.PURC_ORDER_ID
       AND rl.PURC_ORDER_LINE_NO = pol.LINE_NO
       AND pl.RECEIVER_ID = rl.RECEIVER_ID
       AND pl.RECEIVER_LINE_NO = rl.LINE_NO
    LEFT JOIN Live.dbo.RECEIVER AS r
        ON po.ID = r.PURC_ORDER_ID
       AND r.ID = rl.RECEIVER_ID
    LEFT JOIN Live.dbo.PART AS part
        ON part.ID = pol.PART_ID
    INNER JOIN Live.dbo.VENDOR AS v
        ON po.VENDOR_ID = v.ID
    LEFT JOIN Live.dbo.USER_DEF_FIELDS AS ud
        ON pol.PART_ID = ud.DOCUMENT_ID
       AND ud.ID = 'UDF-0000082'
       AND ud.PROGRAM_ID = 'VMPRTMNT'
    WHERE 1 = 1
      AND po.VENDOR_ID <> 'TMXDIV'
      -- Optional filters for ad hoc narrowing:
      -- AND r.RECEIVED_DATE >= DATE '2026-01-01'
      -- AND rl.RECEIVER_ID IS NULL
      -- AND rl.RECEIVER_ID = '215915'
      -- AND pol.PURC_ORDER_ID = '186675'
      -- AND rl.INVOICE_ID IS NULL
)
SELECT
    VENDOR_ID,
    PURC_ORDER_ID,
    LINE_NO,
    RECEIVER_ID,
    ORDER_DATE,
    RCVR_LINE,
    RCVR_INVOICE,
    RECEIVED_DATE,
    VOUCHER_ID,
    PAYABLE_INVOICE,
    DESIRED_RECV_DATE,
    COMMODITY_CODE,
    CONTROLLED,
    SUPPLIER_TYPE,
    PART_ID,
    PLANNER_USER_ID,
    PRODUCT_TYPE,
    TRANSACTION_ID
FROM payables_invoice_voucher_flow
ORDER BY
    VENDOR_ID,
    PURC_ORDER_ID,
    LINE_NO
LIMIT 1000;
