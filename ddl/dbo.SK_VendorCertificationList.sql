CREATE TABLE [dbo].[SK_VendorCertificationList] (
    [ID] int IDENTITY(1,1) DEFAULT  NOT NULL,
    [VendorCertification] NVARCHAR(255) DEFAULT  NOT NULL,
    [Description] NVARCHAR(255) DEFAULT  NULL
)

ALTER TABLE [dbo].[SK_VendorCertificationList] ADD CONSTRAINT [PK_SK_VendorCertificationList] PRIMARY KEY ([ID]);
