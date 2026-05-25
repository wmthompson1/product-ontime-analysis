SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
SET DEADLOCK_PRIORITY LOW;

WITH wo AS (
  SELECT *
  FROM dbo.WORK_ORDER WITH (NOLOCK)
  WHERE [TYPE] = N'W'
    AND [STATUS] IN (N'R', N'F', N'U')
),
pud AS (
  SELECT *
  FROM dbo.USER_DEF_FIELDS
  WHERE PROGRAM_ID IN (N'VMPRTMNT', N'VMMFGWIN_WO', N'VMMFGWIN_OP')
)
SELECT
  wonum.wonum,
  w.STATUS,
  w.part_id,
  w.desired_want_date,
  p.buyer_user_id AS buyer_user_id,
  RTRIM(p.planner_user_id) AS planner_user_id,
  p.commodity_code,
  p.[description],
  b.Salesperson_ID
FROM wo AS w
INNER JOIN part AS p
  ON p.id = w.part_id
LEFT OUTER JOIN [sql-lab-2].livesupplemental.dbo.buyer_assn AS b
  ON LEFT(p.buyer_user_id, 2) = b.account_id
OUTER APPLY (
  SELECT TOP 1
    NULLIF(pud2.string_val, '') AS material
  FROM pud AS pud2
  JOIN part AS p2 ON p2.id = pud2.document_id
  WHERE pud2.id IN (N'UDF-0000035')
    AND pud2.program_id = N'VMPRTMNT'
    AND pud2.document_id IS NOT NULL
    AND pud2.document_id = w.part_id
) AS material
OUTER APPLY (
  SELECT TOP 1
    NULLIF(pud3.string_val, '') AS alloy
  FROM pud AS pud3
  JOIN part AS p3 ON p3.id = pud3.document_id
  WHERE pud3.id IN (N'UDF-0000036')
    AND pud3.program_id = N'VMPRTMNT'
    AND pud3.document_id IS NOT NULL
    AND pud3.document_id = w.part_id
) AS alloy
CROSS APPLY (
  SELECT
    w.base_id
    + CASE WHEN ISNULL(w.sub_id, '0') = '0' THEN '' ELSE '-' + w.sub_id END
    + '/' + w.lot_id
    + CASE WHEN ISNULL(w.split_id, '0') = '0' THEN '' ELSE '.' + w.split_id END
) AS wonum (wonum);