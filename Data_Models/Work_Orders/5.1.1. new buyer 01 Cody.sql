USE [LIVESupplemental]
GO

/****** Object:  Table [dbo].[buyer_assn]    Script Date: 1/19/2026 1:20:10 PM ******/

-- SELECT * FROM  [dbo].[buyer_assn]
--SET ANSI_NULLS ON
--GO

--SET QUOTED_IDENTIFIER ON
--GO

--CREATE TABLE [dbo].[buyer_assn](
--	[Account_ID] [nvarchar](5) NOT NULL,
--	[Salesperson_ID] [nvarchar](255) NOT NULL,
--	[USER_ID] [nvarchar](50) NULL,
--	[Business_Unit] [nvarchar](10) NULL,
--)


USE [LIVESupplemental]
GO
begin transaction
INSERT INTO [dbo].[buyer_assn]
           ([Account_ID]
           ,[Salesperson_ID]
           ,[USER_ID]
           ,[Business_Unit])
     VALUES
           ('01'
           ,'Cody'
           ,'CodyB'
           ,'MFG')
--commit transaction

