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

declare @PART_ID NVARCHAR(50) = null; -- 'BACB30FM6-7';
declare @cc_in nvarchar(255) = 'Raw material, Standards, Details';

WITH CTE_PART AS
(
    SELECT ID FROM PART 
WHERE 1=1 
AND (ID = @PART_ID or @PART_ID IS NULL)
and COMMODITY_CODE IN (
    SELECT LTRIM(RTRIM(value))
    FROM STRING_SPLIT(@cc_in, ',')
)
),

CTE_USER_DEF_FIELDS AS (
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
)

-- -- Create a Common Table Expression (CTE) to pivot USER_DEF_FIELDS for PROGRAM_ID = 'VMVNDMNT'
-- WITH CTE_USER_DEF_FIELDS AS (
--     SELECT
--         VENDOR_ID,
--         MAX(CASE WHEN FIELD_NAME = 'UDF-0000090' THEN FIELD_VALUE END) AS HasVndLimited,
--         MAX(CASE WHEN FIELD_NAME = 'UDF-0000093' THEN FIELD_VALUE END) AS VendorCertKey1,
--         MAX(CASE WHEN FIELD_NAME = 'UDF-0000094' THEN FIELD_VALUE END) AS VendorCertExp1,
--         MAX(CASE WHEN FIELD_NAME = 'UDF-0000095' THEN FIELD_VALUE END) AS VendorCertKey2,
--         MAX(CASE WHEN FIELD_NAME = 'UDF-0000096' THEN FIELD_VALUE END) AS VendorCertExp2,
--         MAX(CASE WHEN FIELD_NAME = 'UDF-0000097' THEN FIELD_VALUE END) AS VendorCertKey3,
--         MAX(CASE WHEN FIELD_NAME = 'UDF-0000098' THEN FIELD_VALUE END) AS VendorCertExp3,
--         MAX(CASE WHEN FIELD_NAME = 'UDF-0000102' THEN FIELD_VALUE END) AS VendorQCNotes
--     FROM Live.dbo.USER_DEF_FIELDS
--     WHERE PROGRAM_ID = 'VMVNDMNT'
--     GROUP BY VENDOR_ID
-- )

SELECT P.ID AS PART_ID
    , P.[DESCRIPTION]
	, UDF.[qc_notes]
    , P.[STATUS]
    , P.STOCK_UM AS UM
    , P.[PRODUCT_CODE]
    , P.[COMMODITY_CODE]
    , P.[FABRICATED]
    , P.[PURCHASED]
    , P.[STOCKED]
    , P.[TOOL_OR_FIXTURE]
    , P.[PLANNER_USER_ID]
    , P.[BUYER_USER_ID]
    , P.CONSUMABLE
    , P.INSPECTION_REQD AS INSP_REQD
--> PART_SITE JOIN FOR UNIT COSTS
    , PS.[UNIT_PRICE]
    , PS.[UNIT_MATERIAL_COST]
    , PS.[UNIT_LABOR_COST]
    , PS.[UNIT_SERVICE_COST]
--> PART SPECIFICATIONS AS DEFINED BY CUSTOMER
    , CAST(CAST(PB.BITS AS VARBINARY(MAX)) AS NVARCHAR(MAX)) AS PART_SPECS
--> DOCUMENTATION OF PART SPECIFICATIONS
    , STUFF((SELECT ', ' + d.id +' REV '+ d.REVISION_ID 
        FROM DOCUMENT D
        INNER JOIN DOCUMENT_REFERENCE DF
            ON DF.DOCUMENT_ID = D.ID
            AND D.CATEGORY_ID = 'SPECIFICATION'
        WHERE P.ID = DF.ID
        FOR XML PATH('')), 1, 1, ''
    ) AS SPEC_LIST
    , P.USER_1 AS TBD1
    , P.USER_2 AS MFG_PROCESS
    , P.USER_3 AS FIN_PROCESS
    , P.USER_4 AS MFG_EST_UNIT_PRICE
    , P.USER_5 AS FIN_EST_UNIT_PRICE
    , P.USER_6 AS TBD2
    , P.USER_7 AS AIRPLANE_MODEL
    , P.USER_8 AS TBD3
    , P.USER_9 AS GEN_PROCESS
    , P.USER_10 AS CUSTOMER_ROLT
    , CASE
        WHEN ISNULL(P.QTY_ON_HAND, 0.00000000) != 0.00000000 THEN P.QTY_ON_HAND
        ELSE 0.00000000
    END AS INVENTORY
    , UDF.[Surface Area]
    , UDF.[Material Type]
    , UDF.[Alloy]
    , UDF.[Length]
    , UDF.[Width]
    , UDF.[Thickness]
    , CASE
        WHEN UDF.[ITAR] = 1 THEN 'ITAR'
        ELSE ''
    END AS [ITAR]
    , UDF.[SK-PUR CONTROLLED]
    , UDF.[SK-PUR Cert Needed]
    , UDF.[Used on Part ID]
    , UDF.[Limited Scope]
    , UDF.[SK-FIN Primer]
    , UDF.[SK-FIN Topcoat]
    , UDF.[SK-FIN Topcoat 2]
FROM CTE_PART CP
JOIN PART P
    ON P.ID = CP.ID    
LEFT OUTER JOIN PART_SITE PS
    ON P.ID = PS.PART_ID
LEFT OUTER JOIN PART_BINARY PB
    ON P.ID = PB.PART_ID
    AND PB.[TYPE] = 'D'
LEFT OUTER JOIN CTE_USER_DEF_FIELDS UDF
    ON P.ID = UDF.DOCUMENT_ID
GO


