    SELECT 
        -- Keys to identify OPERATION
        o.WORKORDER_BASE_ID,
        o.WORKORDER_LOT_ID,
        o.WORKORDER_SPLIT_ID,
        o.WORKORDER_SUB_ID,
        o.WORKORDER_TYPE,
        o.SEQUENCE_NO,
        o.OPERATION_TYPE      AS OPERATION_TYPE_ID,
        o.RESOURCE_ID,

      --  DesiredBits = otb.BITS,
        CurrentBits = ob.BITS,  -- <-- only if OPERATION has BITS
        [BITS_LENGTH] = ob.Bits_length,
		bits_lengthx = DATALENGTH(ob.bits),
	    CAST(CAST(ob.BITS AS varbinary(max)) AS nvarchar(max)) as m_spec
      
    FROM dbo.OPERATION o
    JOIN dbo.OPERATION_TYPE ot
        ON o.OPERATION_TYPE = ot.ID
      -- AND o.RESOURCE_ID    = ot.RESOURCE_ID
  --  JOIN dbo.OPER_TYPE_BINARY otb
  --      ON otb.OPERATION_TYPE_ID = o.OPERATION_TYPE
    inner join OPERATION_BINARY ob
        on ob.WORKORDER_BASE_ID = o.WORKORDER_BASE_ID
        and ob.WORKORDER_lot_ID = o.WORKORDER_lot_ID
        and ob.WORKORDER_split_ID = o.WORKORDER_split_ID
        and ob.WORKORDER_sub_ID = o.WORKORDER_sub_ID
        and ob.WORKORDER_type = o.WORKORDER_type
        and ob.SEQUENCE_NO = o.SEQUENCE_NO


    WHERE 1=1
      AND (@WorkorderBaseId IS NULL OR o.WORKORDER_BASE_ID = @WorkorderBaseId)
      AND (@OperationTypeId IS NULL OR o.OPERATION_TYPE    = @OperationTypeId)