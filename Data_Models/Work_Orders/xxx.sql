
 SELECT * FROM
(
	  SELECT w.type, w.base_id, w.lot_id, w.split_id, w.part_id, w.status,
		/**********
		 w.sub_id, 
		**********/
	  (
		SELECT d.id+CASE WHEN d.revision_id IS NULL THEN ' / REV: ' ELSE ' / REV: '+d.revision_id
			END+CASE WHEN u1.string_val IS NULL or u1.STRING_VAL = '-' THEN ''
			ELSE ' / ADCN: '+u1.string_val END+CASE WHEN u2.string_val IS NULL
			THEN ' / LOC: ' ELSE ' / LOC: '+u2.string_val END+CASE
			WHEN u3.string_val IS NULL THEN '' ELSE ' / '+u3.string_val
			END+CASE WHEN u4.string_val IS NULL THEN ''
			ELSE ' / '+u4.string_val END+CHAR(10)
		FROM [SQL-Lab-2].[LIVEARC].dbo.document_ref_wo AS drw
			JOIN [SQL-Lab-2].[LIVEARC].dbo.document AS d ON drw.document_id = d.id
			LEFT JOIN [SQL-Lab-2].[LIVEARC].dbo.user_def_fields AS u1 ON d.id = u1.document_id
				AND u1.program_id = 'VMDOCMNT' AND u1.id = 'UDF-0000032'
			LEFT JOIN [SQL-Lab-2].[LIVEARC].dbo.user_def_fields AS u2 ON d.id = u2.document_id
				AND u2.program_id = 'VMDOCMNT' AND u2.id = 'UDF-0000031'
			LEFT JOIN [SQL-Lab-2].[LIVEARC].dbo.user_def_fields AS u3 ON d.id = u3.document_id
				AND u3.program_id = 'VMDOCMNT' AND u3.id = 'UDF-0000033'
			LEFT JOIN [SQL-Lab-2].[LIVEARC].dbo.user_def_fields AS u4 ON d.id = u4.document_id
				AND u4.program_id = 'VMDOCMNT' AND u4.id = 'UDF-0000034'
		WHERE  drw.workorder_base_id = w.part_id AND drw.workorder_lot_id = ps.engineering_mstr
				 AND drw.workorder_split_id = '0' AND drw.workorder_type = 'M'
		/*****************************
		 AND DRW.WORKORDER_SUB_ID = 0 
		*****************************/
		FOR XML PATH('')
	  ) AS wo_link,
		(
		    SELECT d.id+CASE WHEN d.revision_id IS NULL THEN ' / REV: '
				ELSE ' / REV: '+d.revision_id END+CASE WHEN u1.string_val IS NULL or u1.STRING_VAL = '-'
				THEN '' ELSE ' / ADCN: '+u1.string_val END+CHAR(10)
		    FROM   [SQL-Lab-2].[LIVEARC].dbo.document_ref_wo AS drw
				JOIN [SQL-Lab-2].[LIVEARC].dbo.document AS d ON drw.document_id = d.id
				LEFT JOIN [SQL-Lab-2].[LIVEARC].dbo.user_def_fields AS u1 ON d.id = u1.document_id
				    AND u1.program_id = 'VMDOCMNT' AND u1.id = 'UDF-0000032'
				LEFT JOIN [SQL-Lab-2].[LIVEARC].dbo.user_def_fields AS u2 ON d.id = u2.document_id
					AND u2.program_id = 'VMDOCMNT' AND u2.id = 'UDF-0000031'
		    WHERE  drw.workorder_base_id = w.part_id AND drw.workorder_lot_id = '0'
				 AND drw.workorder_split_id = '0' AND drw.workorder_type = 'M'
				 AND drw.SEQUENCE_NO = 0 AND drw.PIECE_NO = 0
			/******************************
			 AND  DRW.WORKORDER_SUB_ID = 0 
			******************************/
		    FOR XML PATH('')
	  ) AS wo_link_no_loc 
	  FROM [SQL-Lab-2].[LIVEARC].dbo.work_order AS w
		JOIN [SQL-Lab-2].[LIVEARC].dbo.part AS p ON w.part_id = p.id
		JOIN [SQL-Lab-2].[LIVEARC].dbo.part_site AS ps ON p.id = ps.part_id AND ps.SITE_ID = 'SK01'
	  WHERE type = 'W'
) AS x WHERE wo_link IS NOT NULL --and x.BASE_ID = '1771342' 

;



