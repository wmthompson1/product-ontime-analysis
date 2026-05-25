SELECT 
*
FROM [SQL-LAB-1].Live.dbo.Application_Global

-- "Controlled Product?","Approval Status","Approval Exp(yyyy/mm/dd)","ITAR Exp (yyyy/mm/dd)","DPD Exp (yyyy/mm/dd)","Supplier Type","Product Type"
-- ,"Approvals","See IT (UDF 9)","See IT (UDF 10)"

SELECT [ROWID]
      ,[PROGRAM_ID]
      ,[FIELD_ID]
      ,[FIELD_DESCRIPTION]
  FROM [LIVE].[dbo].[APPLICATION_FIELDS]