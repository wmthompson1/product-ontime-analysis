CREATE TABLE [dbo].[SK_task_audit] (
    [rowid] int IDENTITY(1,1) DEFAULT  NOT NULL,
    [type] NVARCHAR(15) DEFAULT  NULL,
    [task_no] int DEFAULT  NULL,
    [seq_no] int DEFAULT  NULL,
    [user_id_assigned] NVARCHAR(20) DEFAULT  NULL,
    [EC_id] NVARCHAR(128) DEFAULT  NULL,
    [status] NVARCHAR(5) DEFAULT  NULL,
    [completed_date] datetime DEFAULT  NULL,
    [create_date] datetime DEFAULT  NULL,
    [event_user] NVARCHAR(30) DEFAULT  NULL,
    [event_type] NVARCHAR(1) DEFAULT  NULL,
    [event_date] datetime DEFAULT  NULL
)
