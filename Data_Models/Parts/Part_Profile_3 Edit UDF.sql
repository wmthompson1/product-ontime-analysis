USE [LIVE]
GO

SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

/**
2:59:59 PM
Started executing query at  Line 9
(3934 rows affected)
Total execution time: 00:00:00.274
**/

---DECLARE @PART_ID NVARCHAR(50) = 'BACB30FM6-7';
DECLARE @cc_in NVARCHAR(255) = 'Raw material, Standards, Details';

BEGIN TRY
    BEGIN TRANSACTION;

    WITH CTE_PART AS
    (
        SELECT ID, COMMODITY_CODE, [DESCRIPTION], status
        FROM PART
        WHERE 1 = 1
          AND status = 'A'
          --- AND (ID = @PART_ID OR @PART_ID IS NULL)
          AND COMMODITY_CODE IN (
              SELECT LTRIM(RTRIM(value))
              FROM STRING_SPLIT(@cc_in, ',')
          )
    )
    
    -- qc_notes
    UPDATE UDF101
    SET STRING_VAL = CASE 
                        WHEN UDF101.STRING_VAL IS NOT NULL THEN RTRIM(UDF101.STRING_VAL) + ', ' + N'C36'
                        ELSE N'C36'
                     END
    FROM USER_DEF_FIELDS UDF101
    JOIN CTE_PART P
        ON P.ID = UDF101.DOCUMENT_ID
        AND UDF101.PROGRAM_ID = 'VMPRTMNT'
        AND UDF101.ID = 'UDF-0000101'
    WHERE 1 = 1
	;
     --- AND P.ID = @PART_ID;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    -- Rollback the transaction in case of an error
    IF @@TRANCOUNT > 0
        ROLLBACK TRANSACTION;

    -- Print error details
    DECLARE @ErrorMessage NVARCHAR(4000) = ERROR_MESSAGE();
    DECLARE @ErrorSeverity INT = ERROR_SEVERITY();
    DECLARE @ErrorState INT = ERROR_STATE();

    RAISERROR (@ErrorMessage, @ErrorSeverity, @ErrorState);
END CATCH;
GO


