USE [LIVE]
GO

/****** Object:  View [dbo].[vw_PART_DATA]    Script Date: 1/30/2026 12:10:47 PM ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

/**
AI Generated SQL View to consolidate Part data for reporting and analysis. This view combines data from the PART, 
PART_SITE, PART_BINARY, DOCUMENT, DOCUMENT_REFERENCE, and USER_DEF_FIELDS tables to provide a comprehensive dataset 
for each part, including specifications, costs, inventory levels, and user-defined fields.

The query in Part_Profile_2.sql has been refactored to consolidate the USER_DEF_FIELDS joins by pivoting the 
data into a single CTE_USER_DEF_FIELDS. This should improve performance and readability. 
Let me know if you need further adjustments or optimizations!

**/

----CREATE VIEW [dbo].[vw_PART_DATA] AS 

declare @PART_ID NVARCHAR(50) = NULL; -- 'BACB30FM6-7';
DECLARE @VENDOR_ID NVARCHAR(50) = NULL;  ---'3VPREC';
declare @PURC_ORD_ID NVARCHAR(50) = NULL; --- '180033';
declare @cc_in nvarchar(255) = 'raw material, Standards, Details';
DECLARE @START_DATE DATE = '2026-05-01'; 
DECLARE @END_DATE DATE = GETDATE();

WITH CTE_PO AS
(

SELECT po.ID as PURC_ORD_ID, po.VENDOR_ID, po.ORDER_DATE, POL.PART_ID, pol.LINE_NO PO_LINE_NO, po.rowid
       ,p.COMMODITY_CODE
FROM PURCHASE_ORDER PO
LEFT OUTER JOIN PURC_ORDER_LINE POL
	ON PO.ID = POL.PURC_ORDER_ID 
LEFT OUTER JOIN PART P
	ON POL.PART_ID = P.ID
LEFT OUTER JOIN EMPLOYEE EE
	ON PO.BUYER = EE.[USER_ID]
WHERE 1=1 
and (pol.part_id = @part_id or @PART_ID is null)
AND (po.ID = @PURC_ORD_ID OR @PURC_ORD_ID IS NULL)
--and (p.COMMODITY_CODE in (@cc_in)) -- --  ('raw material', 'Standards', 'Details')
 AND (PO.ORDER_DATE >= @START_DATE OR @START_DATE IS NULL)
 AND (PO.ORDER_DATE <= @END_DATE OR @END_DATE IS NULL)

and p.COMMODITY_CODE IN (
    SELECT LTRIM(RTRIM(value))
    FROM STRING_SPLIT(@cc_in, ',')
)

),
CTE_VENDOR AS
(SELECT v.ID 
FROM VENDOR v
JOIN CTE_PO po
ON Po.VENDOR_ID = V.ID
WHERE 1=1   
--AND v.ID = @VENDOR_ID
),
 CTE_USER_DEF_FIELDS_VMPRTMNT AS (
     SELECT
         DOCUMENT_ID,
         MAX(CASE WHEN ID = 'UDF-0000026' THEN STRING_VAL ELSE NULL END) AS [Surface Area],
         MAX(CASE WHEN ID = 'UDF-0000035' THEN STRING_VAL ELSE NULL END) AS [Material Type],
         MAX(CASE WHEN ID = 'UDF-0000036' THEN STRING_VAL ELSE NULL END) AS [Alloy],
         MAX(CASE WHEN ID = 'UDF-0000037' THEN STRING_VAL ELSE NULL END) AS [Length],
         MAX(CASE WHEN ID = 'UDF-0000038' THEN STRING_VAL ELSE NULL END) AS [Width],
         MAX(CASE WHEN ID = 'UDF-0000039' THEN STRING_VAL ELSE NULL END) AS [Thickness],
         MAX(CASE WHEN ID = 'UDF-0000040' THEN BOOL_VAL ELSE NULL END) AS [ITAR],
         MAX(CASE WHEN ID = 'UDF-0000082' THEN STRING_VAL ELSE NULL END) AS [SK-PUR CONTROLLED],
         MAX(CASE WHEN ID = 'UDF-0000084' THEN STRING_VAL ELSE NULL END) AS [SK-PUR Cert Needed],
         MAX(CASE WHEN ID = 'UDF-0000085' THEN STRING_VAL ELSE NULL END) AS [Used on Part ID],
         MAX(CASE WHEN ID = 'UDF-0000091' THEN STRING_VAL ELSE NULL END) AS [Limited Scope],
         MAX(CASE WHEN ID = 'UDF-0000092' THEN STRING_VAL ELSE NULL END) AS [SK-FIN Primer],
         MAX(CASE WHEN ID = 'UDF-0000098' THEN STRING_VAL ELSE NULL END) AS [SK-FIN Topcoat],
         MAX(CASE WHEN ID = 'UDF-0000099' THEN STRING_VAL ELSE NULL END) AS [SK-FIN Topcoat 2],
		 MAX(CASE WHEN ID = 'UDF-0000101' THEN STRING_VAL ELSE NULL END) AS [qc_notes]

     FROM USER_DEF_FIELDS
     WHERE PROGRAM_ID = 'VMPRTMNT'
     GROUP BY DOCUMENT_ID
 ),

-- Create a Common Table Expression (CTE) to pivot USER_DEF_FIELDS for PROGRAM_ID = 'VMVNDMNT'
 CTE_USER_DEF_FIELDS AS (
    SELECT
        DOCUMENT_ID,
    -- Pivot USER_DEF_FIELDS AND DETERMINE TYPE (STRING_VAL, BOOL_VAL, etc.) BASED ON actual sql uaws in SQL_Reports
        MAX(CASE WHEN ID = 'UDF-0000026' THEN STRING_VAL END) AS [Surface Area],
        MAX(CASE WHEN ID = 'UDF-0000090' THEN BOOL_VAL END)   AS HasVndLimited,
        MAX(CASE WHEN ID = 'UDF-0000093' THEN STRING_VAL END) AS VendorCertKey1,
        MAX(CASE WHEN ID = 'UDF-0000094' THEN STRING_VAL END) AS VendorCertExp1,
        MAX(CASE WHEN ID = 'UDF-0000095' THEN STRING_VAL END) AS VendorCertKey2,
        MAX(CASE WHEN ID = 'UDF-0000096' THEN STRING_VAL END) AS VendorCertExp2,
        MAX(CASE WHEN ID = 'UDF-0000097' THEN STRING_VAL END) AS VendorCertKey3,
        MAX(CASE WHEN ID = 'UDF-0000098' THEN STRING_VAL END) AS VendorCertExp3,
        MAX(CASE WHEN ID = 'UDF-0000102' THEN STRING_VAL END) AS VendorQCNotes
    FROM Live.dbo.USER_DEF_FIELDS
    WHERE PROGRAM_ID = 'VMVNDMNT'
    GROUP BY DOCUMENT_ID
)

SELECT
       V.ID AS VENDOR_ID
	  ,Po.PURC_ORD_ID
	  , po.PO_LINE_NO
	  ,po.COMMODITY_CODE
	  ,row_number() over (partition by Po.PURC_ORD_ID, po.PO_LINE_NO
									order by po.rowid) as rn
	  , po.ORDER_DATE
	  ,udf.VendorQCNotes
	  ,x.[qc_notes]
	  ,po.PART_ID
      ,v.NAME
      ,v.ADDR_1
      ,v.ADDR_2
      ,v.ADDR_3
      ,v.CITY
      ,v.STATE
      ,v.ZIPCODE

      ,v.OPEN_DATE
      ,v.MODIFY_DATE
      ,v.USER_1
      ,v.USER_2
      ,v.USER_3
      ,v.USER_4
      ,v.USER_5
      ,v.USER_6
      ,v.USER_7
      ,v.USER_8
      ,v.USER_9
      ,v.USER_10
	  ,'VMPRTMNT -->>' note
	  ,x.*
FROM CTE_PO po
join CTE_VENDOR filterVendor
on po.VENDOR_ID = filterVendor.ID 
join VENDOR v
on V.ID = filterVendor.ID
LEFT OUTER JOIN CTE_USER_DEF_FIELDS UDF
    ON V.ID = UDF.DOCUMENT_ID

LEFT JOIN CTE_USER_DEF_FIELDS_VMPRTMNT x
  on po.PART_ID = x.document_id
;



