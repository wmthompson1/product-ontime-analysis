	-- Perspective: Engineering
	-- Description: Engineering Masters
	-- Comment: added where a.CREATE_DATE >= '2026-02-01' for brevity
    SELECT 
         a.CREATE_DATE
		,a.STATUS
        ,a.BASE_ID
        ,a.LOT_ID
        ,a.SUB_ID
        ,a.SPLIT_ID
		,a.PART_ID
	from dbo.WORK_ORDER a
	where 1=1
	and a.CREATE_DATE >= '2026-02-01'
    AND a.TYPE = 'M'