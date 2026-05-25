CREATE TABLE [dbo].[tmpInvQty] (
    [TxID] bigint DEFAULT  NULL,
    [part_id] NVARCHAR(30) DEFAULT  NULL,
    [Qty] DECIMAL(38,8) DEFAULT  NULL,
    [warehouse_id] NVARCHAR(15) DEFAULT  NULL,
    [location_id] NVARCHAR(15) DEFAULT  NULL
)
