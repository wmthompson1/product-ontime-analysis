-- find atc certs
select 
    L.id as load_id
    ,L.cust_order_id
    ,C.name as customer_name
    
 from       customer_order O
 --on            L.cust_order_id = O.id 

 join            customer C
 on            O.customer_id = C.id