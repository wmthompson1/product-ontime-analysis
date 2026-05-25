CREATE TABLE [dbo].[SK_PartCertificationsList] (
    [ID] int IDENTITY(1,1) DEFAULT  NOT NULL,
    [Certifications] NVARCHAR(255) DEFAULT  NOT NULL,
    [Description] NVARCHAR(255) DEFAULT  NULL
)

ALTER TABLE [dbo].[SK_PartCertificationsList] ADD CONSTRAINT [PK_SK_PartCertificationsList] PRIMARY KEY ([ID]);
