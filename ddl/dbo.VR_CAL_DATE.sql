CREATE TABLE [dbo].[VR_CAL_DATE] (
    [ROWID] int IDENTITY(1,1) DEFAULT  NOT NULL,
    [CAL_DAY] datetime DEFAULT  NOT NULL,
    [CAL_WEEK] datetime DEFAULT  NULL,
    [CAL_MONTH] datetime DEFAULT  NULL,
    [CAL_QUARTER] datetime DEFAULT  NULL,
    [CAL_YEAR] int DEFAULT  NULL
)
