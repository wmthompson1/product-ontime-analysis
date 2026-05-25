-- Visual Enterprise Reports>Part Reports>Part_Inventory_Qty
/**
12/10/2025 WilliamT

**/

    DECLARE  @warehouse		NVARCHAR(50) = 'Auburn Mtl Cage';
    DECLARE  @location      NVARCHAR(50) = NULL;
    DECLARE  @comm          NVARCHAR(50) = NULL;


SELECT P.ID,
       P.DESCRIPTION,
       CASE
       WHEN P.COMMODITY_CODE IS NULL 
           THEN 'NULL'
           ELSE P.COMMODITY_CODE
       END AS COMMODITY_CODE,
       P.ABC_CODE,
       PL.WAREHOUSE_ID,
       PL.LOCATION_ID,
       PL.STATUS,
       PL.QTY,
       P.FABRICATED,
       p.PLANNER_USER_ID,
       p.BUYER_USER_ID,
       P.STOCK_UM,
       P.PURCHASED
  FROM
       PART_LOCATION AS PL
 INNER JOIN PART AS P
       ON PL.PART_ID=P.ID
  WHERE 1=1
  AND  PL.QTY <> 0  

        AND (PL.WAREHOUSE_ID = @warehouse    OR  @warehouse	  IS NULL)
        AND (P.COMMODITY_CODE = @comm     OR  @comm is null ) 
    
        AND (PL.LOCATION_ID = @location    OR  @location	  IS NULL)    
             
 -- ORDER BY P.ID,PL.LOCATION_ID;