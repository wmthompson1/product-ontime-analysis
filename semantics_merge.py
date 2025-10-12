"""
python semantics_merge.py 


"""

import os
import re
import random
import openai

from langchain.indexes import VectorstoreIndexCreator
from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings
from langchain_experimental.text_splitter import SemanticChunker

# Import OpenAI client and initialize with your API key.
from openai import OpenAI

# Load environment from .env if python-dotenv is available. If not, fall back to env vars.
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    # python-dotenv not installed or .env not present; proceed using environment variables
    pass

# Read API key from environment
api_key = os.getenv("OPENAI_API_KEY")
# api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print(
        'WARNING: OPENAI_API_KEY not set. Set it in a .env file or environment variables.'
    )

dialogues = []

# https://www.freecodecamp.org/news/prompt-engineering-cheat-sheet-for-gpt-5/

import json

# USING CoPilot_with_GPT5
#client = CoPilot_with_GPT5
client = OpenAI(api_key=api_key) if api_key else None


def generate_schema_list(template_schema_data,
                         template_candidate_keys,
                         target_schema_data,
                         target_candidate_keys=None):
    prompt = f"""
    You are an expert at converting schema information into a script using SQL Server syntax.

    Generate Script according to the following rules:
    - Use SQL Server syntax.
    - Use the following format for the script:

    Template schema Information:
    {template_schema_data}

    Template Candidate Keys:
    {template_candidate_keys if template_candidate_keys else "None"}  

Template: 

CREATE OR ALTER PROCEDURE dbo.Merge_Labor_Tickets_NetChanges_All
    @from_lsn varbinary(10),
    @to_lsn   varbinary(10)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    -- Capture instance used in your example:
    DECLARE @Cap sysname = N'dbo_LABOR_TICKET';

    -- (Optional) quick sanity guards
    DECLARE @min_lsn varbinary(10) = sys.fn_cdc_get_min_lsn(@Cap);
    DECLARE @max_lsn varbinary(10) = sys.fn_cdc_get_max_lsn();
    IF @from_lsn IS NULL OR @to_lsn IS NULL
        THROW 50001, 'from_lsn/to_lsn cannot be NULL.', 1;
    IF @from_lsn < @min_lsn
        THROW 50002, 'from_lsn is below current CDC window (retention).', 1;
    IF @to_lsn   > @max_lsn
        SET @to_lsn = @max_lsn;

    -- Build delta set from net-changes (1=del, 2=ins, 4=upd)
    IF OBJECT_ID('tempdb..#Labor_Tickets_Delta') IS NOT NULL DROP TABLE #Labor_Tickets_Delta;
    CREATE TABLE #Labor_Tickets_Delta
    (
        LaborTicketID          int            NOT NULL,
        ROWID                  int            NULL,
        TRANSACTION_ID         int            NULL,
        WORKORDER_TYPE         nchar(1)       NULL,
        WORKORDER_BASE_ID      nvarchar(30)   NULL,
        WORKORDER_LOT_ID       nvarchar(3)    NULL,
        WORKORDER_SPLIT_ID     nvarchar(3)    NULL,
        WORKORDER_SUB_ID       nvarchar(3)    NULL,
        Op                     tinyint        NOT NULL,        -- 1/2/4
        CommitLsn              varbinary(10)  NOT NULL,
        CommitTime             datetime       NULL
    );

    INSERT #Labor_Tickets_Delta
    (
        LaborTicketID, ROWID, TRANSACTION_ID, WORKORDER_TYPE, WORKORDER_BASE_ID,
        WORKORDER_LOT_ID, WORKORDER_SPLIT_ID, WORKORDER_SUB_ID,
        Op, CommitLsn, CommitTime
    )
    SELECT
        nc.LaborTicketID,
        nc.ROWID,
        nc.TRANSACTION_ID,
        nc.WORKORDER_TYPE,
        nc.WORKORDER_BASE_ID,
        nc.WORKORDER_LOT_ID,
        nc.WORKORDER_SPLIT_ID,
        nc.WORKORDER_SUB_ID,
        nc.__$operation                 AS Op,            -- 1=del, 2=ins, 4=upd
        nc.__$start_lsn                 AS CommitLsn,
        sys.fn_cdc_map_lsn_to_time(nc.__$start_lsn) AS CommitTime
    FROM cdc.fn_cdc_get_net_changes_dbo_LABOR_TICKET(@from_lsn, @to_lsn, N'all') AS nc;
    -- In 'all', __$update_mask is always NULL; in 'all with mask', mask is populated. 

    BEGIN TRAN;

    -- MERGE: DELETE → UPDATE → INSERT
    MERGE dbo.Labor_Tickets_Base AS T
    USING #Labor_Tickets_Delta   AS S
      ON S.TRANSACTION_ID = T.TRANSACTION_ID

    -- 1) Apply deletes
    WHEN MATCHED AND S.Op = 1 THEN
        DELETE

    -- 2) Apply updates (op = 4)
    WHEN MATCHED AND S.Op = 4 THEN
        UPDATE SET
            T.ROWID                 = S.ROWID,
            T.WORKORDER_TYPE        = S.WORKORDER_TYPE,
            T.WORKORDER_BASE_ID     = S.WORKORDER_BASE_ID,
            T.WORKORDER_LOT_ID      = S.WORKORDER_LOT_ID,
            T.WORKORDER_SPLIT_ID    = S.WORKORDER_SPLIT_ID,
            T.WORKORDER_SUB_ID      = S.WORKORDER_SUB_ID,
            T.LastCdcCommitLsn      = S.CommitLsn,
            T.LastCdcCommitTime     = S.CommitTime

    -- 3) Apply inserts (op = 2)
    WHEN NOT MATCHED BY TARGET AND S.Op = 2 THEN
        INSERT
        (
            ROWID, TRANSACTION_ID, WORKORDER_TYPE, WORKORDER_BASE_ID,
            WORKORDER_LOT_ID, WORKORDER_SPLIT_ID, WORKORDER_SUB_ID,
            LastCdcCommitLsn, LastCdcCommitTime
        )
        VALUES
        (
            S.ROWID, S.TRANSACTION_ID, S.WORKORDER_TYPE, S.WORKORDER_BASE_ID,
            S.WORKORDER_LOT_ID, S.WORKORDER_SPLIT_ID, S.WORKORDER_SUB_ID,
            S.CommitLsn, S.CommitTime
        )

    OUTPUT $action AS MergeAction, inserted.TRANSACTION_ID, S.Op, S.CommitLsn, S.CommitTime;

    COMMIT TRAN;
END



    target schema Information:
    {target_schema_data}

    target Candidate Keys:
    {target_candidate_keys if target_candidate_keys else "None"}  


    """

    response = client.responses.create(model="gpt-5", input=prompt)

    print(response.output_text)

    # Try to parse the response
    try:
        text_output = response.output_text
        return text_output
    except:
        print(f"Error parsing text output: {response.output_text}")
        return None


# template schema
template_schema_data = """
    [ROWID] [int] NULL,
    [TRANSACTION_ID] [int] NULL,
    [WORKORDER_TYPE] [nchar](1) NULL,
    [WORKORDER_BASE_ID] [nvarchar](30) NULL,
    [WORKORDER_LOT_ID] [nvarchar](3) NULL,
    [WORKORDER_SPLIT_ID] [nvarchar](3) NULL,
    [WORKORDER_SUB_ID] [nvarchar](3) NUL
"""

# template candidate keys
template_candidate_keys = """
    [TRANSACTION_ID] [int]
    """

# target template schema
target_schema_data = """

CREATE TABLE [dbo].[CUSTOMER](
    [ROWID] [int] IDENTITY(1,1) NOT NULL,
    [ID] [nvarchar](15) NOT NULL,
    [NAME] [nvarchar](50) NULL,
    [ADDR_1] [nvarchar](50) NULL,
    [ADDR_2] [nvarchar](50) NULL,
    [ADDR_3] [nvarchar](50) NULL,
    [CITY] [nvarchar](30) NULL,
    [STATE] [nvarchar](10) NULL,
    [ZIPCODE] [nvarchar](10) NULL,
    [COUNTRY] [nvarchar](50) NULL,

    )  
"""

# target candidate keys
target_candidate_keys = """
    [ID] [int]


"""

schema_list = generate_schema_list(template_schema_data,
                                   template_candidate_keys, target_schema_data,
                                   target_candidate_keys)
if schema_list:
    print(schema_list)
