SELECT
    NCM.ncm_id,
    NCM.incident_date,
    E.FIRST_NAME,
    E.LAST_NAME
FROM non_conformant_materials NCM
    LEFT OUTER JOIN EMPLOYEE E
        ON E.ID = NCM.ASSIGNED_EMPLOYEE_ID;