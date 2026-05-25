
-- C:\20200908 Ann Packlist Form Report\
-- C:\20200908 Ann Packlist Form Report\packlist form report.1.sql
-- C:\20200908 Ann Packlist Form Report\packlist form report.2.sql

/**********************************************************************************************
Description:    By packlist ID
Sample:            

Date        Modified By         Change Description
----------  ------------------  ------------------------------------------------------------
9/14/2020    William Thompson    Created from profiler.
9/14/2020    William Thompson    Ann requested transactions shipped - > join inventory_trans

Filter: join to transactions (shipped)

[Singleton] = 1 ,  -- level 0

O.id -- one to many -- > 

 FROM       shipper_line SL -- level 1
 join       shipper S
 on            SL.packlist_id = S.packlist_id 

 join        cust_order_line L   -- level 2
 on            S.cust_order_id = L.cust_order_id 

     SELECT dw_Ship_From_Id, dw_Ship_From
    FROM (VALUES
          (1, 'Plant 1')
        , (2, 'Plant 2')
        , (3, 'Plant 3')
        ) AS sub 
        (dw_Ship_From_Id, dw_Ship_From)

Sold to Address
-----------------
NAME
addr_1
addr_2
addr_3
city
state
zipcode


Ship to Address
-----------------
Ship_To_NAME
Ship_To_ADDR_1
Ship_To_ADDR_2
Ship_To_ADDR_3
Ship_To_CITY
Ship_To_STATE
Ship_To_ZIPCODE

**********************************************************************************************/


SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED
SET DEADLOCK_PRIORITY LOW

IF OBJECT_ID('tempdb..#Results') IS NOT NULL DROP TABLE #Results

-- Test Header -------------------------------
DECLARE @Packlist_ID NVARCHAR(15) = '1492864';  ---- '1447859' -- NULL
declare @dw_Ship_From_Id int =  NULL; -- 1, 2, 3 for ship from
-- Test header ends //////////////////////////

SELECT         
                [Singleton] = 1 ,  -- level 0
                S.packlist_id, 
                SL.line_no, 
                Isnull ( SL.cust_order_line_no, SL.line_no ) CO_line_no, 
                SL.cust_order_line_no  cust_order_line_no, 
                O.id cust_order_id, 
                O.customer_id, 
                S.invoiced_date, 
                S.shipped_date, 
                C.[NAME], 
                C.addr_1, 
                C.addr_2, 
                C.addr_3, 
                C.city, 
                C.state, 
                C.zipcode, 
                C.country, 
                C.customer_country_id, 
                S.ship_to_addr_no, 
                S.site_id, 
                Isnull ( S.sales_tax_group_id, O.sales_tax_group_id ) SO_sales_tax_group_id, 
                O.contact_honorific, 
                O.contact_first_name, 
                O.contact_last_name, 
                O.contact_initial, 
                O.order_date, 
                O.desired_ship_date O_desired_ship_date, 
                O.promise_date O_promise_date, 
                O.promise_del_date O_promise_del_date, 
                Isnull ( S.salesrep_id, O.salesrep_id ) salesrep_id, 
                Isnull ( S.free_on_board, O.free_on_board ) free_on_board, 
                Isnull ( S.ship_via, O.ship_via ) ship_via, 
                O.terms_net_type, 
                O.terms_net_days, 
                O.terms_net_date, 
                O.terms_disc_type, 
                O.terms_disc_days, 
                O.terms_disc_date, 
                O.terms_disc_percent, 
                O.terms_description, 
                O.customer_po_ref,   -- po
                O.[status], 
                O.consignment, 

                L.edi_release_no, 
                Isnull ( L.part_id, SL.service_charge_id ) product_id, 
                P.[description], 
                L.selling_um, 
                P.stock_um, 
                Isnull ( SL.misc_reference, L.misc_reference ) misc_reference, 
                L.user_order_qty, 
                Isnull ( SL.unit_price, L.unit_price ) unit_price, 
                SL.user_shipped_qty, 
                Isnull ( SL.trade_disc_percent, L.trade_disc_percent ) trade_disc_percent, 
                Isnull ( SL.sales_tax_group_id, L.sales_tax_group_id ) SLL_sales_tax_group_id, 
                O.carrier_id, 
                 o.user_1     o_user_1 
                ,o.user_2     o_user_2 
                ,o.user_3     o_user_3 
                ,o.user_4     o_user_4 
                ,o.user_5     o_user_5 
                ,o.user_6     o_user_6 
                ,o.user_7     o_user_7 
                ,o.user_8     o_user_8 
                ,o.user_9     o_user_9 
                ,o.user_10    o_user_10,
                 L.user_1     L_user_1 
                ,L.user_2     L_user_2   -- po line
                ,L.user_3     L_user_3 
                ,L.user_4     L_user_4 
                ,L.user_5     L_user_5 
                ,L.user_6     L_user_6 
                ,L.user_7     L_user_7 
                ,L.user_8     L_user_8 
                ,L.user_9     L_user_9 
                ,L.user_10    L_user_10,
                SL.act_freight, 
                SL.ship_dimensions, 
                L.customer_part_id, 
                SL.transaction_id, 
                L.desired_ship_date L_desired_ship_date, 
                L.promise_date L_promise_date, 
                L.promise_del_date L_promise_del_date, 
                 C.user_1     C_user_1 
                ,C.user_2     C_user_2 
                ,C.user_3     C_user_3 
                ,C.user_4     C_user_4 
                ,C.user_5     C_user_5 
                ,C.user_6     C_user_6 
                ,C.user_7     C_user_7 
                ,C.user_8     C_user_8 
                ,C.user_9     C_user_9 
                ,C.user_10    C_user_10,
                C.tax_id_number, 
                P.[weight], 
                P.weight_um, 
                 p.user_1     p_user_1 
                ,p.user_2     p_user_2 
                ,p.user_3     p_user_3 
                ,p.user_4     p_user_4 
                ,p.user_5     p_user_5 
                ,p.user_6     p_user_6 
                ,p.user_7     p_user_7 
                ,p.user_8     p_user_8 
                ,p.user_9     p_user_9 
                ,p.user_10    p_user_10, 
                SL.shipping_weight, 
                SL.carton_count, 
                O.sell_rate, 
                SL.net_ship_weight, 
                SL.pallet_count, 
                C.pool_code C_pool_code, 
                C.inter_consignee C_inter_consignee, 
                S.customs_doc_id, 
                S.waybill_number, 
                S.pool_code S_pool_code, 
                S.vehicle_number, 
                S.inter_consignee S_inter_consignee, 
                S.total_net_weight, 
                S.total_gross_weight, 
                SL.tare_weight, 
                C.backorder_flag, 
                s.user_1     s_user_1 
                ,s.user_2     s_user_2 
                ,s.user_3     s_user_3 
                ,s.user_4     s_user_4 
                ,s.user_5     s_user_5 
                ,s.user_6     s_user_6 
                ,s.user_7     s_user_7 
                ,s.user_8     s_user_8 
                ,s.user_9     s_user_9 
                ,s.user_10    s_user_10,
                 sl.user_1     sl_user_1 
                ,sl.user_2     sl_user_2 
                ,sl.user_3     sl_user_3 
                ,sl.user_4     sl_user_4 
                ,sl.user_5     sl_user_5 
                ,sl.user_6     sl_user_6 
                ,sl.user_7     sl_user_7 
                ,sl.user_8     sl_user_8 
                ,sl.user_9     sl_user_9 
                ,sl.user_10    sl_user_10,
                SL.nmfc_code_id, 
                SL.package_type, 
 
                SL.shipping_um, 
                SL.piece_count, 
                SL.[length], 
                SL.width, 
                SL.height, 
                SL.dimensions_um, 
                SL.rma_id, 
                SL.rma_line_no, 
                P.drawing_id, 
                P.drawing_rev_no, 
                C.vat_registration, 
 

                 Ship_To.[NAME] Ship_To_NAME
                ,Ship_To.[ADDR_1] Ship_To_ADDR_1
                ,Ship_To.[ADDR_2] Ship_To_ADDR_2
                ,Ship_To.[ADDR_3] Ship_To_ADDR_3
                ,Ship_To.CITY Ship_To_CITY
                ,Ship_To.[STATE] Ship_To_STATE
                ,Ship_To.[ZIPCODE] Ship_To_ZIPCODE
                ,Ship_To.COUNTRY Ship_To_COUNTRY

                , linked.SUPPLY_BASE_ID
                , linked.SUPPLY_LOT_ID
                , linked.SUPPLY_SPLIT_ID 

                ,Allocation_Type = CASE
                    WHEN linked.DEMAND_BASE_ID IS NULL AND linked.DEMAND_SEQ_NO IS NULL AND linked.DEMAND_TYPE IS NULL
                    THEN N'Unlinked' END

                , dw_ship_from.dw_Ship_From_Name
                , dw_ship_from.dw_Ship_From_Addr
                , dw_ship_from.dw_Ship_From_City
                , dw_ship_from.dw_Ship_From_State
                , dw_ship_from.dw_Ship_From_Zip
                 -- payment terms logic
                 ,case 
                when O.terms_description is not null then
                  CONVERT(NVARCHAR(80),O.terms_description)
                when O.terms_net_days > 0 then
                  'Net ' + CONVERT(NVARCHAR(80), O.terms_net_days )
                else
                  NULL
                end dw_payment_terms
                ,dw_backorder_override = 0


 FROM       shipper_line SL -- level 1 packlist_id
 join       shipper S
 on            SL.packlist_id = S.packlist_id 

 join        cust_order_line L   -- level 2  cust_order_line_no
 on            S.cust_order_id = L.cust_order_id
 and        SL.cust_order_line_no = L.line_no  

 join       customer_order O
 on            L.cust_order_id = O.id 

 join            customer C
 on            O.customer_id = C.id

LEFT OUTER JOIN part P 
ON              L.part_id = P.id 

inner JOIN dbo.INVENTORY_TRANS T
    ON SL.TRANSACTION_ID = T.TRANSACTION_ID

-- Ship_To
-- level 1
OUTER APPLY (
SELECT TOP 1
  [NAME], ADDR_1, ADDR_2, ADDR_3, CITY, STATE, ZIPCODE, COUNTRY, CUST_ADDR_COUNTRY_ID
, CONSOL_SHIP_LINE, POOL_CODE, TRANS_METHOD_CODE, INTER_CONSIGNEE, POOL_POINT_ID, SUPPLIER_ID
, DOCK_CODE_FIELD, DUTY_BROKERAGE, MATERIAL_ISSUER, EQUIPMENT_DESCR, LADING_CODE, MODEL_YEAR, HANDLING_ID
, ALLOW_CHARGE_NO, NON_RETURN_CODE, MIXED_CODE, TRADING_PARTNER, TRANSIT_TIME
, USER_1, USER_2, USER_3, USER_4, USER_5, USER_6, USER_7, USER_8, USER_9, USER_10
, CARRIER_ID, SHIP_VIA 
FROM CUST_ADDRESS ca
WHERE ca.CUSTOMER_ID = O.customer_id  -- 'AERMAN'  -- @P1 
AND ca.ADDR_NO = S.ship_to_addr_no  --  6  -- @P2
) Ship_To

-- if linked wo
-- level 2
OUTER APPLY (
SELECT SUPPLY_BASE_ID, SUPPLY_LOT_ID, SUPPLY_SPLIT_ID, dsl.DEMAND_BASE_ID, dsl.DEMAND_SEQ_NO, dsl.DEMAND_TYPE 
FROM DEMAND_SUPPLY_LINK dsl
 WHERE dsl.DEMAND_TYPE = N'CO' 
AND dsl.DEMAND_BASE_ID = o.id  -- '458195' --  @P1 co order id
AND dsl.DEMAND_SEQ_NO = SL.cust_order_line_no -- 1 -- @P2 -- co line
AND dsl.SUPPLY_TYPE = N'WO'
/**
    ,Allocation_Type = CASE
        WHEN linked.DEMAND_BASE_ID IS NULL AND linked.DEMAND_SEQ_NO IS NULL AND linked.DEMAND_TYPE IS NULL
        THEN N'Unlinked' END
**/

) linked

OUTER APPLY (
    SELECT 
    X.*
    from (
            select
             dw_Ship_From_Id = 3
            ,dw_Ship_From_Name = 'Skills, Inc.'
            ,dw_Ship_From_Addr= '1316 West Main Street' 
            ,dw_Ship_From_City = 'Auburn'
            ,dw_Ship_From_State = 'WA'
            ,dw_Ship_From_Zip = '98001'
            union all
            --Skills, Inc.
            --425 C Street NW
            --Auburn, WA 98001
            select
             dw_Ship_From_Id = 2
            ,dw_Ship_From_Name = 'Skills, Inc.'
            ,dw_Ship_From_Addr= '425 C Street NW' 
            ,dw_Ship_From_City = 'Auburn'
            ,dw_Ship_From_State = 'WA'
            ,dw_Ship_From_Zip = '98001'
            union all
            --715 30th Street NE
            --Auburn, WA 98002
             select
             dw_Ship_From_Id = 1
            ,dw_Ship_From_Name = 'Skills, Inc.'
            ,dw_Ship_From_Addr= '715 30th Street NE' 
            ,dw_Ship_From_City = 'Auburn'
            ,dw_Ship_From_State = 'WA'
            ,dw_Ship_From_Zip = '98002'
        ) X
        where (dw_Ship_From_Id = isnull(@dw_Ship_From_Id,1))
        
) dw_ship_from


WHERE   (1=1)  
and (sl.PACKLIST_ID = @Packlist_ID or @Packlist_ID IS NULL)
and (invoiced_date is null or invoiced_date >= -- first of the month six months prior   
dateadd(month, -6, dateadd(day, 1 - day(getdate()), cast(getdate() as date))))  
-- unlinked logic  
and linked.DEMAND_BASE_ID IS NULL AND linked.DEMAND_SEQ_NO IS NULL AND linked.DEMAND_TYPE IS NULL
--AND             SL.packlist_id = S.packlist_id 
AND             S.site_id = 'SK01' -- @P1 
--AND             S.cust_order_id = L.cust_order_id 
--AND             SL.cust_order_line_no = L.line_no 
--AND             L.cust_order_id = O.id 
--AND             O.customer_id = C.id

AND (SL.PACKLIST_ID = @Packlist_ID  OR @Packlist_ID IS NULL)
AND             ( ( 
                            Isnull ( S.ship_to_addr_no, O.ship_to_addr_no ) IS NULL
            AND             C.language_id IS NULL ) 
OR              ( 
                            Isnull ( S.ship_to_addr_no, O.ship_to_addr_no ) IS NOT NULL
            AND             Isnull ( S.ship_to_addr_no, O.ship_to_addr_no ) IN
                            ( 
                                    SELECT addr_no 
                                    FROM   cust_address 
                                    WHERE  customer_id = C.id 
                                    AND    addr_no = Isnull ( S.ship_to_addr_no, O.ship_to_addr_no )
                                    AND    language_id IS NULL ) ) ) 
test_logic_terms:

--SELECT
--                O.terms_net_type, 
--                O.terms_net_days, 
--                O.terms_net_date, 
--                O.terms_disc_type, 
--                O.terms_disc_days, 
--                O.terms_disc_date, 
--                O.terms_disc_percent, 
--                O.terms_description
--                                 ,case 
--                when O.terms_description is not null then
--                  CONVERT(NVARCHAR(80),O.terms_description)
--                when O.terms_net_days > 0 then
--                  'Net ' + CONVERT(NVARCHAR(80), O.terms_net_days )
--                else
--                  NULL
--                end dw_payment_terms
--        INTO #RESULTS
-- FROM       shipper_line SL (nolock) -- level 1 packlist_id
-- join       shipper S (NOLOCK)
-- on            SL.packlist_id = S.packlist_id 

-- join        cust_order_line L   -- level 2  cust_order_line_no
-- on            S.cust_order_id = L.cust_order_id
-- and        SL.cust_order_line_no = L.line_no  

-- join       customer_order O
-- on            L.cust_order_id = O.id 

-- join            customer C
-- on            O.customer_id = C.id

--LEFT OUTER JOIN part P 
--ON              L.part_id = P.id 

-- SELECT 
--                   O.terms_net_type, 
--                O.terms_net_days, 
--                O.terms_net_date, 
--                O.terms_disc_type, 
--                O.terms_disc_days, 
--                O.terms_disc_date, 
--                O.terms_disc_percent, 
--                O.terms_description,
--                dw_payment_terms
--FROM #RESULTS o (NOLOCK)
--group by
--                   O.terms_net_type, 
--                O.terms_net_days, 
--                O.terms_net_date, 
--                O.terms_disc_type, 
--                O.terms_disc_days, 
--                O.terms_disc_date, 
--                O.terms_disc_percent, 
--                O.terms_description,
--                dw_payment_terms

--profile_backorder_flag:
--select C.backorder_flag, * from CUSTOMER C 
--where BACKORDER_FLAG = 'Y'
--group by C.BACKORDER_FLAG
