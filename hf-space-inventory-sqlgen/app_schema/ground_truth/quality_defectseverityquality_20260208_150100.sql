SELECT
    d.defect_id,
    d.severity_level,
    d.defect_type,
    d.root_cause,
    d.quality_score
FROM defect_records d
WHERE d.severity_level IN ('Critical', 'Major', 'Minor')
