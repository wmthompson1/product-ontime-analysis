-- Focused: Operation-Type text cleanup and 2nd-line / 2nd-paragraph extraction
-- Returns: OTB_Text, OTB_Body_Clean, Paragraph2, Line2

SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
SET DEADLOCK_PRIORITY LOW;

DECLARE @OPTYPE NVARCHAR(MAX) = 'F20.03'; -- set to NULL to run all

SELECT
    otb.OPERATION_TYPE_ID,
    DATALENGTH(otb.BITS) AS OTB_Bytes,
    OTB_Text = CAST(CAST(otb.BITS AS varbinary(max)) AS nvarchar(max)),
    CA.OTB_Body_Clean,
    -- Paragraph2 and Line2 computed below
    Paragraph2 = CASE
        WHEN P.first2 = 0 THEN NULL
        WHEN P.second2 = 0 THEN SUBSTRING(CA.OTB_Body_Clean, P.first2 + 2, LEN(CA.OTB_Body_Clean) - (P.first2 + 1))
        ELSE SUBSTRING(CA.OTB_Body_Clean, P.first2 + 2, P.second2 - (P.first2 + 2))
    END,
    Line2 = CASE
        WHEN L.first1 = 0 THEN NULL
        WHEN L.second1 = 0 THEN SUBSTRING(CA.OTB_Body_Clean, L.first1 + 1, LEN(CA.OTB_Body_Clean) - L.first1)
        ELSE SUBSTRING(CA.OTB_Body_Clean, L.first1 + 1, L.second1 - (L.first1 + 1))
    END
FROM dbo.OPER_TYPE_BINARY otb
CROSS APPLY (
    -- Normalize CRLF -> LF, remove tabs, collapse whitespace-only blank lines into double-LF
    SELECT CASE WHEN otb.BITS IS NULL THEN NULL ELSE
        REPLACE(
            REPLACE(
                REPLACE(
                    REPLACE(
                        REPLACE(REPLACE(CAST(CAST(otb.BITS AS varbinary(max)) AS nvarchar(max)), CHAR(13) + CHAR(10), CHAR(10)), CHAR(13), CHAR(10)),
                    CHAR(9), ''),
                CHAR(10) + ' ' + CHAR(10), CHAR(10) + CHAR(10)),
            CHAR(10) + '  ' + CHAR(10), CHAR(10) + CHAR(10)),
        CHAR(10) + '   ' + CHAR(10), CHAR(10) + CHAR(10)) END as OTB_Body_Clean
) CA
CROSS APPLY (
    SELECT
        CHARINDEX(CHAR(10) + CHAR(10), CA.OTB_Body_Clean) AS first2,
        CASE WHEN CHARINDEX(CHAR(10) + CHAR(10), CA.OTB_Body_Clean) = 0 THEN 0
             ELSE CHARINDEX(CHAR(10) + CHAR(10), CA.OTB_Body_Clean, CHARINDEX(CHAR(10) + CHAR(10), CA.OTB_Body_Clean) + 2)
        END AS second2
) P
CROSS APPLY (
    SELECT
        CHARINDEX(CHAR(10), CA.OTB_Body_Clean) AS first1,
        CASE WHEN CHARINDEX(CHAR(10), CA.OTB_Body_Clean) = 0 THEN 0
             ELSE CHARINDEX(CHAR(10), CA.OTB_Body_Clean, CHARINDEX(CHAR(10), CA.OTB_Body_Clean) + 1)
        END AS second1
) L
WHERE 1=1
--- (otb.OPERATION_TYPE_ID IN (@OPTYPE) OR @OPTYPE IS NULL)
ORDER BY otb.OPERATION_TYPE_ID;
