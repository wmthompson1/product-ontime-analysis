CREATE TABLE [dbo].[tmpRcvrClear] (
    [vendor_id] NVARCHAR(15) DEFAULT  NOT NULL,
    [Voucher] NVARCHAR(24) DEFAULT  NOT NULL,
    [VoucherLnNo] bigint DEFAULT  NULL,
    [PurcOrderID] NVARCHAR(15) DEFAULT  NULL,
    [PoLn] smallint DEFAULT  NULL,
    [unit_price] DECIMAL(38,9) DEFAULT  NULL,
    [received_qty] DECIMAL(20,8) DEFAULT  NOT NULL,
    [fixedCharge] DECIMAL(23,8) DEFAULT  NOT NULL,
    [Amount] DECIMAL(38,6) DEFAULT  NULL,
    [receiver_id] NVARCHAR(15) DEFAULT  NULL,
    [RcvrLineNo] smallint DEFAULT  NULL
)
