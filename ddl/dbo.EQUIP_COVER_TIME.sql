CREATE TABLE [dbo].[EQUIP_COVER_TIME] (
    [ROWID] int IDENTITY(1,1) DEFAULT  NOT NULL,
    [coverage_id] smallint DEFAULT  NOT NULL,
    [start_time] datetime DEFAULT  NOT NULL,
    [end_time] datetime DEFAULT  NOT NULL,
    [description] NVARCHAR(30) DEFAULT  NULL
)

ALTER TABLE [dbo].[EQUIP_COVER_TIME] ADD CONSTRAINT [pk_eq_cover_time] PRIMARY KEY ([coverage_id]);
