CREATE TABLE [dbo].[boe_pay_summary_history](
	[boeing invoice num] [nvarchar](20) NULL,
	[boeing purchase order num] [nvarchar](20) NULL,
	[supplier invoice num] [nvarchar](25) NULL,
	[invoice received date] [date] NULL,
	[invoice gross amt] [money] NULL,
	[applied disc amt] [money] NULL,
	[invoice net amt] [money] NULL,
	[conversion rate] [decimal](18, 3) NULL,
	[check/trace num] [nvarchar](10) NULL,
	[site supplier code] [nvarchar](10) NULL,
	[best code] [nvarchar](10) NULL,
	[payment/check date] [date] NULL,
	[payment settlement date] [date] NULL,
	[payment] [money] NULL,
	[invoices paid] [int] NULL,
	[payment status] [nvarchar](50) NULL,
	[import date] [datetime] NULL
) ON [PRIMARY]
GO