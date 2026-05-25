CREATE TABLE [dbo].[systranschemas] (
    [tabid] int DEFAULT  NOT NULL,
    [startlsn] binary DEFAULT  NOT NULL,
    [endlsn] binary DEFAULT  NOT NULL,
    [typeid] int DEFAULT ((52)) NOT NULL
)
