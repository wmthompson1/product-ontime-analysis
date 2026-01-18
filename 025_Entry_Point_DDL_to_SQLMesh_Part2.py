"""
025 - Mock Data Generator for Manufacturing Digital Twin (Part 2)
=================================================================
Generates realistic mock data for the manufacturing schema to populate
the SQLMesh staging models. Creates DuckDB-compatible seed data.

Usage:
    python 025_Entry_Point_DDL_to_SQLMesh_Part2.py [--rows N] [--output-dir PATH] [--preview]

Features:
    - Uses Faker for realistic synthetic data generation
    - Generates realistic manufacturing metrics (OEE, MTBF, defect rates)
    - Maintains referential integrity across tables
    - Creates time-series data with configurable date ranges
    - Outputs CSV seeds for SQLMesh SEED models

Part II Enhancements:
    - Faker-powered company names, contacts, addresses
    - Manufacturing-specific Faker providers
    - Complete coverage for all 26 staging tables
"""

import os
import csv
import random
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Optional
from faker import Faker


# Configuration
DEFAULT_START_DATE = datetime(2024, 1, 1)
DEFAULT_END_DATE = datetime(2024, 12, 31)
DEFAULT_ROWS_PER_TABLE = 100


class MockConfig:
    """Configuration for mock data generation."""
    def __init__(
        self,
        start_date: datetime = DEFAULT_START_DATE,
        end_date: datetime = DEFAULT_END_DATE,
        rows_per_table: int = DEFAULT_ROWS_PER_TABLE,
        output_dir: str = "Utilities/SQLMesh/seeds",
        seed: int = 42
    ):
        self.start_date = start_date
        self.end_date = end_date
        self.rows_per_table = rows_per_table
        self.output_dir = output_dir
        self.seed = seed
        self.fake = Faker()
        Faker.seed(seed)
        random.seed(seed)


# Realistic manufacturing data pools
SUPPLIERS = [
    ("Precision Parts Inc.", "precision@parts.com", "555-0101", "Detroit, MI"),
    ("Global Components Ltd.", "sales@globalcomp.com", "555-0102", "Shanghai, China"),
    ("AeroTech Materials", "info@aerotech.com", "555-0103", "Seattle, WA"),
    ("Quality Fasteners Co.", "qfc@fasteners.com", "555-0104", "Cleveland, OH"),
    ("Advanced Alloys LLC", "contact@advalloys.com", "555-0105", "Pittsburgh, PA"),
    ("Midwest Manufacturing", "orders@midwestmfg.com", "555-0106", "Chicago, IL"),
    ("Pacific Precision", "sales@pacificprec.com", "555-0107", "Los Angeles, CA"),
    ("Eastern Electronics", "info@easternelec.com", "555-0108", "Boston, MA"),
]

PRODUCT_LINES = [
    ("Turbine Blades", "Aerospace", 5000, 2500.00, 0.35),
    ("Landing Gear", "Aerospace", 200, 45000.00, 0.28),
    ("Hydraulic Actuators", "Industrial", 1500, 850.00, 0.32),
    ("Control Valves", "Industrial", 3000, 420.00, 0.40),
    ("Precision Bearings", "Automotive", 10000, 125.00, 0.45),
    ("Sensor Assemblies", "Electronics", 8000, 75.00, 0.38),
    ("Composite Panels", "Aerospace", 800, 3200.00, 0.30),
    ("Engine Mounts", "Automotive", 4000, 280.00, 0.35),
]

PRODUCTION_LINES = [
    ("Line A - Main Assembly", "Building 1", "Assembly", 500),
    ("Line B - Precision Machining", "Building 1", "Machining", 200),
    ("Line C - Heat Treatment", "Building 2", "Processing", 300),
    ("Line D - Quality Inspection", "Building 2", "Inspection", 400),
    ("Line E - Packaging", "Building 3", "Packaging", 600),
    ("Line F - CNC Center", "Building 1", "Machining", 150),
]

EQUIPMENT_TYPES = [
    "CNC Lathe", "Milling Machine", "Robotic Arm", "Conveyor System",
    "Hydraulic Press", "Laser Cutter", "Heat Treatment Oven", "CMM",
    "Assembly Robot", "Packaging Machine", "Quality Scanner", "Welding Station"
]

DEFECT_TYPES = [
    "Surface Scratch", "Dimensional Out-of-Spec", "Material Contamination",
    "Weld Defect", "Missing Component", "Incorrect Assembly", "Coating Failure",
    "Stress Crack", "Porosity", "Thread Damage"
]

FAILURE_MODES = [
    "Bearing Wear", "Motor Burnout", "Sensor Malfunction", "Hydraulic Leak",
    "Belt Snap", "Controller Failure", "Overheating", "Vibration Damage",
    "Electrical Short", "Calibration Drift"
]

DOWNTIME_CATEGORIES = [
    "Planned Maintenance", "Unplanned Breakdown", "Material Shortage",
    "Quality Hold", "Changeover", "Operator Unavailable", "Power Outage"
]

SEVERITY_LEVELS = ["Critical", "Major", "Minor"]
STATUS_OPTIONS = ["Open", "In Progress", "Resolved", "Closed"]
SHIFTS = ["Day", "Swing", "Night"]


def random_date(start: datetime, end: datetime) -> datetime:
    """Generate a random datetime between start and end."""
    delta = end - start
    random_days = random.randint(0, delta.days)
    random_seconds = random.randint(0, 86400)
    return start + timedelta(days=random_days, seconds=random_seconds)


def random_date_only(start: datetime, end: datetime) -> str:
    """Generate a random date string."""
    return random_date(start, end).strftime("%Y-%m-%d")


def random_datetime(start: datetime, end: datetime) -> str:
    """Generate a random datetime string."""
    return random_date(start, end).strftime("%Y-%m-%d %H:%M:%S")


def generate_suppliers(config: MockConfig) -> list[dict]:
    """Generate supplier reference data using Faker."""
    fake = config.fake
    data = []
    
    mfg_suffixes = ["Manufacturing", "Components", "Industries", "Precision", "Materials", 
                   "Systems", "Technologies", "Aerospace", "Solutions", "Metalworks"]
    certifications = ["AS9100", "ISO9001", "IATF16949", "ISO13485", "NADCAP", "ISO14001"]
    
    for i in range(1, config.rows_per_table + 1):
        company_base = fake.company().split()[0]
        company_name = f"{company_base} {random.choice(mfg_suffixes)}"
        
        data.append({
            "supplier_id": i,
            "supplier_name": company_name,
            "contact_email": fake.company_email(),
            "phone": fake.phone_number(),
            "address": f"{fake.street_address()}, {fake.city()}, {fake.state_abbr()} {fake.zipcode()}",
            "performance_rating": round(random.uniform(3.5, 5.0), 2),
            "certification_level": random.choice(certifications),
            "lead_time_days": random.randint(3, 45),
            "payment_terms": random.choice(["Net 30", "Net 45", "Net 60", "2/10 Net 30"]),
            "created_date": random_datetime(config.start_date, config.end_date)
        })
    return data


def generate_product_lines(config: MockConfig) -> list[dict]:
    """Generate product line reference data."""
    data = []
    for i, (name, category, volume, price, margin) in enumerate(PRODUCT_LINES, 1):
        data.append({
            "product_line_id": i,
            "product_line_name": name,
            "product_category": category,
            "target_volume": volume,
            "unit_price": price,
            "profit_margin": margin,
            "launch_date": random_date_only(datetime(2020, 1, 1), datetime(2023, 12, 31)),
            "lifecycle_stage": random.choice(["Growth", "Mature", "Decline", "Introduction"]),
            "primary_market": random.choice(["North America", "Europe", "Asia Pacific", "Global"]),
            "complexity_rating": random.choice(["Low", "Medium", "High", "Very High"]),
            "regulatory_requirements": random.choice(["FAA", "EASA", "FDA", "None", "Military"]),
            "created_at": random_datetime(config.start_date, config.end_date)
        })
    return data


def generate_production_lines(config: MockConfig) -> list[dict]:
    """Generate production line reference data using Faker."""
    fake = config.fake
    data = []
    line_types = ["Assembly", "Machining", "Processing", "Inspection", "Packaging", "CNC", "Welding", "Finishing"]
    buildings = ["Building A", "Building B", "Building C", "North Plant", "South Plant", "Main Facility"]
    
    for i in range(1, min(config.rows_per_table, 20) + 1):
        line_type = random.choice(line_types)
        capacity = random.randint(100, 800)
        actual_cap = int(capacity * random.uniform(0.7, 0.95))
        
        data.append({
            "line_id": i,
            "line_name": f"Line {chr(64 + i)} - {line_type}",
            "facility_location": random.choice(buildings),
            "line_type": line_type,
            "theoretical_capacity": capacity,
            "actual_capacity": actual_cap,
            "efficiency_rating": round(actual_cap / capacity * 100, 1),
            "installation_date": random_date_only(datetime(2015, 1, 1), datetime(2022, 12, 31)),
            "last_maintenance_date": random_date_only(config.start_date, config.end_date),
            "status": random.choice(["Active", "Active", "Active", "Maintenance", "Idle"]),
            "supervisor": fake.name(),
            "shift_pattern": random.choice(["3-shift", "2-shift", "Day only", "24/7"]),
            "created_at": random_datetime(config.start_date, config.end_date)
        })
    return data


def generate_daily_deliveries(config: MockConfig, supplier_count: int) -> list[dict]:
    """Generate daily delivery records."""
    data = []
    current_date = config.start_date
    delivery_id = 1
    
    while current_date <= config.end_date:
        # 1-3 deliveries per day
        num_deliveries = random.randint(1, 3)
        for _ in range(num_deliveries):
            supplier_id = random.randint(1, supplier_count)
            planned_qty = random.randint(50, 500)
            # Most deliveries are on time with some variance
            variance = random.gauss(0, 0.1)
            actual_qty = max(0, int(planned_qty * (1 + variance)))
            ontime = 1.0 if random.random() > 0.15 else round(random.uniform(0.5, 0.99), 2)
            
            data.append({
                "delivery_id": delivery_id,
                "supplier_id": supplier_id,
                "delivery_date": current_date.strftime("%Y-%m-%d"),
                "planned_quantity": planned_qty,
                "actual_quantity": actual_qty,
                "ontime_rate": ontime,
                "quality_score": round(random.uniform(0.85, 1.0), 3),
                "created_date": current_date.strftime("%Y-%m-%d %H:%M:%S")
            })
            delivery_id += 1
        
        current_date += timedelta(days=1)
    
    return data


def generate_equipment_metrics(config: MockConfig, line_count: int) -> list[dict]:
    """Generate equipment metrics (OEE data)."""
    data = []
    equipment_id = 1
    
    for line_id in range(1, line_count + 1):
        # 2-4 pieces of equipment per line
        num_equipment = random.randint(2, 4)
        for eq_num in range(num_equipment):
            eq_type = random.choice(EQUIPMENT_TYPES)
            eq_name = f"{eq_type} {line_id}-{eq_num + 1}"
            
            # Generate daily metrics
            current_date = config.start_date
            while current_date <= config.end_date:
                # OEE components with realistic ranges
                availability = round(random.uniform(0.80, 0.98), 3)
                performance = round(random.uniform(0.75, 0.95), 3)
                quality = round(random.uniform(0.90, 0.995), 3)
                oee = round(availability * performance * quality, 3)
                
                data.append({
                    "equipment_id": equipment_id,
                    "line_id": str(line_id),
                    "equipment_type": eq_type,
                    "equipment_name": eq_name,
                    "measurement_date": current_date.strftime("%Y-%m-%d"),
                    "availability_rate": availability,
                    "performance_rate": performance,
                    "quality_rate": quality,
                    "oee_score": oee,
                    "downtime_hours": round((1 - availability) * 24, 2),
                    "created_date": current_date.strftime("%Y-%m-%d %H:%M:%S")
                })
                current_date += timedelta(days=7)  # Weekly metrics
            
            equipment_id += 1
    
    return data


def generate_product_defects(config: MockConfig, product_line_count: int) -> list[dict]:
    """Generate product defect records."""
    data = []
    defect_id = 1
    
    current_date = config.start_date
    while current_date <= config.end_date:
        # 0-3 defect records per day
        num_defects = random.randint(0, 3)
        for _ in range(num_defects):
            product_line = PRODUCT_LINES[random.randint(0, product_line_count - 1)][0]
            total_produced = random.randint(100, 1000)
            defect_count = random.randint(0, int(total_produced * 0.05))
            
            data.append({
                "defect_id": defect_id,
                "product_line": product_line,
                "production_date": current_date.strftime("%Y-%m-%d"),
                "defect_type": random.choice(DEFECT_TYPES),
                "defect_count": defect_count,
                "total_produced": total_produced,
                "defect_rate": round(defect_count / total_produced, 4) if total_produced > 0 else 0,
                "severity": random.choice(SEVERITY_LEVELS),
                "root_cause": random.choice([
                    "Tool wear", "Material variance", "Operator error",
                    "Process deviation", "Environmental factors", "Machine calibration"
                ]),
                "created_date": current_date.strftime("%Y-%m-%d %H:%M:%S")
            })
            defect_id += 1
        
        current_date += timedelta(days=1)
    
    return data


def generate_failure_events(config: MockConfig, equipment_count: int) -> list[dict]:
    """Generate equipment failure events."""
    data = []
    technicians = ["Tech-A", "Tech-B", "Tech-C", "Tech-D", "Tech-E"]
    
    for failure_id in range(1, config.rows_per_table + 1):
        failure_date = random_datetime(config.start_date, config.end_date)
        downtime = round(random.uniform(0.5, 24), 2)
        
        data.append({
            "failure_id": failure_id,
            "equipment_id": random.randint(1, equipment_count),
            "failure_date": failure_date,
            "failure_type": random.choice(["Mechanical", "Electrical", "Software", "Hydraulic", "Pneumatic"]),
            "failure_mode": random.choice(FAILURE_MODES),
            "severity_level": random.choice(SEVERITY_LEVELS),
            "downtime_hours": downtime,
            "repair_cost": round(random.uniform(500, 25000), 2),
            "parts_replaced": random.choice(["Bearing", "Motor", "Sensor", "Belt", "Controller", "None"]),
            "technician_assigned": random.choice(technicians),
            "failure_description": f"Equipment failure requiring {downtime:.1f}h repair",
            "root_cause_analysis": random.choice([
                "Wear and tear", "Improper maintenance", "Overload condition",
                "Environmental stress", "Manufacturing defect", "Under investigation"
            ]),
            "preventive_action": random.choice([
                "Increase inspection frequency", "Replace aging components",
                "Update maintenance schedule", "Operator training", "Process adjustment"
            ]),
            "mtbf_impact": round(random.uniform(-50, 50), 1),
            "created_at": failure_date
        })
    
    return data


def generate_downtime_events(config: MockConfig, line_count: int, equipment_count: int) -> list[dict]:
    """Generate downtime event records."""
    data = []
    reporters = ["Shift Lead A", "Operator B", "Supervisor C", "Maintenance D"]
    
    for event_id in range(1, config.rows_per_table + 1):
        start_time = random_datetime(config.start_date, config.end_date)
        duration = random.randint(15, 480)
        end_time = (datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S") + 
                   timedelta(minutes=duration)).strftime("%Y-%m-%d %H:%M:%S")
        
        data.append({
            "event_id": event_id,
            "line_id": random.randint(1, line_count),
            "equipment_id": random.randint(1, equipment_count),
            "event_start_time": start_time,
            "event_end_time": end_time,
            "downtime_duration_minutes": duration,
            "downtime_category": random.choice(DOWNTIME_CATEGORIES),
            "downtime_reason": f"Reason for {duration} min downtime event",
            "impact_severity": random.choice(SEVERITY_LEVELS),
            "production_loss_units": random.randint(0, 100),
            "cost_impact": round(duration * random.uniform(10, 50), 2),
            "resolution_method": random.choice([
                "Part replacement", "Recalibration", "Software restart",
                "Operator intervention", "Scheduled end", "External support"
            ]),
            "reported_by": random.choice(reporters),
            "created_at": start_time
        })
    
    return data


def generate_quality_incidents(config: MockConfig, product_line_count: int) -> list[dict]:
    """Generate quality incident records."""
    data = []
    assignees = ["QA Lead", "Quality Engineer", "Process Engineer", "Supervisor"]
    detection_methods = ["Visual Inspection", "CMM", "Automated Scanner", "Customer Report", "Audit"]
    
    for incident_id in range(1, config.rows_per_table + 1):
        incident_date = random_date_only(config.start_date, config.end_date)
        product_line = PRODUCT_LINES[random.randint(0, product_line_count - 1)][0]
        is_resolved = random.random() > 0.3
        
        data.append({
            "incident_id": incident_id,
            "product_line": product_line,
            "incident_date": incident_date,
            "incident_type": random.choice([
                "Process Deviation", "Material NCM", "Customer Complaint",
                "Audit Finding", "Specification Change", "Equipment Issue"
            ]),
            "severity_level": random.choice(SEVERITY_LEVELS),
            "affected_units": random.randint(1, 500),
            "cost_impact": round(random.uniform(100, 50000), 2),
            "detection_method": random.choice(detection_methods),
            "status": "Closed" if is_resolved else random.choice(["Open", "In Progress"]),
            "assigned_to": random.choice(assignees),
            "resolution_date": incident_date if is_resolved else "",
            "root_cause": random.choice([
                "Material variance", "Process parameter drift", "Tool wear",
                "Training gap", "Documentation error", "Under investigation"
            ]),
            "created_at": incident_date + " 08:00:00"
        })
    
    return data


def generate_equipment_reliability(config: MockConfig, equipment_count: int) -> list[dict]:
    """Generate equipment reliability metrics (MTBF data)."""
    data = []
    reliability_id = 1
    
    current_date = config.start_date
    while current_date <= config.end_date:
        for eq_id in range(1, equipment_count + 1):
            target_mtbf = random.uniform(500, 2000)
            failure_count = random.randint(0, 5)
            operating_hours = random.uniform(600, 720)
            actual_mtbf = operating_hours / max(failure_count, 1)
            
            data.append({
                "reliability_id": reliability_id,
                "equipment_id": eq_id,
                "measurement_period": current_date.strftime("%Y-%m-%d"),
                "mtbf_hours": round(actual_mtbf, 2),
                "target_mtbf": round(target_mtbf, 2),
                "failure_count": failure_count,
                "operating_hours": round(operating_hours, 2),
                "reliability_score": round(min(actual_mtbf / target_mtbf, 1.0) * 100, 1),
                "created_date": current_date.strftime("%Y-%m-%d %H:%M:%S")
            })
            reliability_id += 1
        
        current_date += timedelta(days=30)  # Monthly metrics
    
    return data


def generate_non_conformant_materials(config: MockConfig, supplier_count: int, product_line_count: int) -> list[dict]:
    """
    Generate Non-Conformant Materials (NCM) data.
    
    NCM vs Defect Pattern:
    - NCM is the material-centric view preferred by Quality perspective
    - stg_product_defects tracks production defects (estimated cost)
    - stg_non_conformant_materials tracks material NCMs (actual cost)
    
    When severity or cost_impact collides, the Perspective elevation
    determines which "Solder" (table) to use:
    - Quality perspective -> NCM.severity (root cause analysis)
    - Finance perspective -> NCM.cost_impact (actual financial liability)
    """
    data = []
    
    material_types = [
        "Titanium Alloy Ti-6Al-4V", "Aluminum 7075-T6", "Inconel 718",
        "Carbon Fiber Composite", "Stainless Steel 304L", "Copper C110",
        "Nickel Superalloy", "Magnesium AZ31B", "Tool Steel D2",
        "Ceramic Matrix Composite"
    ]
    
    ncm_descriptions = [
        "Material hardness below specification - failed Rockwell test",
        "Surface contamination detected - oil residue on raw stock",
        "Dimensional variance exceeds tolerance - undersized bar stock",
        "Grain structure anomaly - improper heat treatment by supplier",
        "Chemical composition out of spec - carbon content high",
        "Incoming inspection failed - visual defects on surface",
        "Certificate of Conformance missing required test data",
        "Lot traceability documentation incomplete",
        "Material substitution without engineering approval",
        "Storage damage - corrosion from improper handling"
    ]
    
    root_causes = [
        "Supplier process deviation",
        "Raw material batch variation",
        "Transportation damage",
        "Storage condition failure",
        "Incoming inspection escape",
        "Documentation error",
        "Supplier change notification missed",
        "Specification interpretation error"
    ]
    
    ncm_id = 1
    current_date = config.start_date
    
    while current_date <= config.end_date:
        num_ncms = random.randint(0, 2)
        
        for _ in range(num_ncms):
            supplier_id = random.randint(1, supplier_count)
            product_line = PRODUCT_LINES[random.randint(0, product_line_count - 1)][0]
            severity = random.choice(SEVERITY_LEVELS)
            
            if severity == "Critical":
                cost_impact = round(random.uniform(5000, 50000), 2)
                quantity = random.randint(50, 500)
            elif severity == "Major":
                cost_impact = round(random.uniform(1000, 10000), 2)
                quantity = random.randint(20, 200)
            else:
                cost_impact = round(random.uniform(100, 2000), 2)
                quantity = random.randint(5, 50)
            
            is_resolved = random.random() > 0.25
            
            data.append({
                "ncm_id": ncm_id,
                "incident_date": current_date.strftime("%Y-%m-%d"),
                "product_line": product_line,
                "supplier_id": supplier_id,
                "material_type": random.choice(material_types),
                "defect_description": random.choice(ncm_descriptions),
                "quantity_affected": quantity,
                "severity": severity,
                "root_cause": random.choice(root_causes),
                "cost_impact": cost_impact,
                "status": "Closed" if is_resolved else random.choice(["Open", "Under Review", "Pending Disposition"]),
                "created_date": current_date.strftime("%Y-%m-%d %H:%M:%S")
            })
            ncm_id += 1
        
        current_date += timedelta(days=1)
    
    return data


def generate_products(config: MockConfig) -> list[dict]:
    """Generate products reference data using Faker."""
    fake = config.fake
    data = []
    
    categories = ["Aerospace", "Industrial", "Automotive", "Electronics", "Defense"]
    statuses = ["Active", "Active", "Active", "Discontinued", "Development", "Pending Approval"]
    
    for i in range(1, config.rows_per_table + 1):
        category = random.choice(categories)
        unit_cost = round(random.uniform(50, 5000), 2)
        
        data.append({
            "product_id": i,
            "product_name": f"{fake.word().title()}-{random.randint(100, 9999)}",
            "product_category": category,
            "unit_cost": unit_cost,
            "unit_price": round(unit_cost * random.uniform(1.2, 2.5), 2),
            "weight_kg": round(random.uniform(0.1, 50), 3),
            "lead_time_days": random.randint(5, 60),
            "min_order_qty": random.choice([1, 5, 10, 25, 50, 100]),
            "status": random.choice(statuses),
            "created_date": random_datetime(config.start_date, config.end_date)
        })
    return data


def generate_production_schedule(config: MockConfig, line_count: int, product_count: int) -> list[dict]:
    """Generate production schedule data using Faker."""
    data = []
    schedule_id = 1
    current_date = config.start_date
    
    while current_date <= config.end_date:
        num_schedules = random.randint(3, 8)
        for _ in range(num_schedules):
            planned_qty = random.randint(50, 500)
            actual_qty = int(planned_qty * random.uniform(0.85, 1.05))
            
            data.append({
                "schedule_id": schedule_id,
                "line_id": random.randint(1, line_count),
                "product_id": random.randint(1, product_count),
                "scheduled_date": current_date.strftime("%Y-%m-%d"),
                "shift": random.choice(SHIFTS),
                "planned_quantity": planned_qty,
                "actual_quantity": actual_qty,
                "completion_rate": round(actual_qty / planned_qty * 100, 1),
                "status": random.choice(["Completed", "Completed", "In Progress", "Scheduled", "Delayed"]),
                "created_date": current_date.strftime("%Y-%m-%d %H:%M:%S")
            })
            schedule_id += 1
        current_date += timedelta(days=1)
    
    return data


def generate_production_quality(config: MockConfig, line_count: int) -> list[dict]:
    """Generate production quality metrics using Faker."""
    data = []
    quality_id = 1
    current_date = config.start_date
    
    while current_date <= config.end_date:
        for line_id in range(1, line_count + 1):
            total_produced = random.randint(100, 1000)
            passed = int(total_produced * random.uniform(0.92, 0.995))
            
            data.append({
                "quality_id": quality_id,
                "line_id": line_id,
                "measurement_date": current_date.strftime("%Y-%m-%d"),
                "total_produced": total_produced,
                "passed_inspection": passed,
                "failed_inspection": total_produced - passed,
                "first_pass_yield": round(passed / total_produced * 100, 2),
                "rework_count": random.randint(0, total_produced - passed),
                "scrap_count": random.randint(0, (total_produced - passed) // 2),
                "created_date": current_date.strftime("%Y-%m-%d %H:%M:%S")
            })
            quality_id += 1
        current_date += timedelta(days=1)
    
    return data


def generate_corrective_actions(config: MockConfig, incident_count: int) -> list[dict]:
    """Generate corrective action records using Faker."""
    fake = config.fake
    data = []
    
    action_types = ["Root Cause Analysis", "Process Change", "Training", "Equipment Calibration", 
                    "Supplier Corrective Action", "Design Change", "Inspection Enhancement"]
    
    for i in range(1, min(config.rows_per_table, incident_count) + 1):
        open_date = random_date(config.start_date, config.end_date)
        is_closed = random.random() > 0.3
        close_date = open_date + timedelta(days=random.randint(7, 90)) if is_closed else None
        
        data.append({
            "action_id": i,
            "incident_id": random.randint(1, incident_count),
            "action_type": random.choice(action_types),
            "description": fake.sentence(nb_words=10),
            "assigned_to": fake.name(),
            "open_date": open_date.strftime("%Y-%m-%d"),
            "due_date": (open_date + timedelta(days=random.randint(14, 60))).strftime("%Y-%m-%d"),
            "close_date": close_date.strftime("%Y-%m-%d") if close_date else None,
            "status": "Closed" if is_closed else random.choice(["Open", "In Progress", "Pending Verification"]),
            "effectiveness_score": round(random.uniform(0.7, 1.0), 2) if is_closed else None,
            "created_date": open_date.strftime("%Y-%m-%d %H:%M:%S")
        })
    return data


def generate_effectiveness_metrics(config: MockConfig, action_count: int) -> list[dict]:
    """Generate effectiveness metrics for corrective actions."""
    data = []
    
    for i in range(1, min(config.rows_per_table, action_count) + 1):
        baseline_rate = round(random.uniform(0.02, 0.10), 4)
        improved_rate = round(baseline_rate * random.uniform(0.3, 0.9), 4)
        
        data.append({
            "metric_id": i,
            "action_id": random.randint(1, action_count),
            "metric_type": random.choice(["Defect Rate", "Cycle Time", "Yield", "Cost Reduction", "MTBF"]),
            "baseline_value": baseline_rate,
            "target_value": round(baseline_rate * 0.5, 4),
            "actual_value": improved_rate,
            "improvement_pct": round((baseline_rate - improved_rate) / baseline_rate * 100, 1),
            "measurement_date": random_date_only(config.start_date, config.end_date),
            "verified_by": config.fake.name(),
            "created_date": random_datetime(config.start_date, config.end_date)
        })
    return data


def generate_quality_costs(config: MockConfig) -> list[dict]:
    """Generate quality cost tracking (Cost of Quality - CoQ)."""
    data = []
    cost_id = 1
    current_date = config.start_date
    
    cost_categories = ["Prevention", "Appraisal", "Internal Failure", "External Failure"]
    
    while current_date <= config.end_date:
        for category in cost_categories:
            if category == "Prevention":
                cost = round(random.uniform(5000, 20000), 2)
            elif category == "Appraisal":
                cost = round(random.uniform(8000, 30000), 2)
            elif category == "Internal Failure":
                cost = round(random.uniform(10000, 50000), 2)
            else:
                cost = round(random.uniform(15000, 75000), 2)
            
            data.append({
                "cost_id": cost_id,
                "cost_category": category,
                "cost_period": current_date.strftime("%Y-%m"),
                "amount": cost,
                "budget": round(cost * random.uniform(0.9, 1.2), 2),
                "variance_pct": round(random.uniform(-15, 15), 1),
                "created_date": current_date.strftime("%Y-%m-%d %H:%M:%S")
            })
            cost_id += 1
        current_date += timedelta(days=30)
    
    return data


def generate_financial_impact(config: MockConfig, ncm_count: int, defect_count: int) -> list[dict]:
    """Generate financial impact records for NCMs and defects."""
    fake = config.fake
    data = []
    
    impact_types = ["Scrap", "Rework", "Warranty Claim", "Customer Credit", "Expedite Cost", "Inspection Cost"]
    
    for i in range(1, config.rows_per_table + 1):
        is_ncm = random.random() > 0.5
        
        data.append({
            "impact_id": i,
            "source_type": "NCM" if is_ncm else "Defect",
            "source_id": random.randint(1, ncm_count if is_ncm else defect_count),
            "impact_type": random.choice(impact_types),
            "impact_date": random_date_only(config.start_date, config.end_date),
            "direct_cost": round(random.uniform(500, 25000), 2),
            "indirect_cost": round(random.uniform(100, 5000), 2),
            "recovery_amount": round(random.uniform(0, 5000), 2),
            "approved_by": fake.name(),
            "created_date": random_datetime(config.start_date, config.end_date)
        })
    return data


def generate_maintenance_targets(config: MockConfig, equipment_count: int) -> list[dict]:
    """Generate maintenance targets for equipment."""
    data = []
    
    for i in range(1, min(config.rows_per_table, equipment_count * 2) + 1):
        data.append({
            "target_id": i,
            "equipment_id": random.randint(1, equipment_count),
            "target_year": random.choice([2024, 2025]),
            "target_mtbf": round(random.uniform(800, 2500), 0),
            "target_availability": round(random.uniform(0.92, 0.98), 3),
            "target_oee": round(random.uniform(0.75, 0.90), 3),
            "pm_interval_days": random.choice([7, 14, 30, 60, 90]),
            "created_date": random_datetime(config.start_date, config.end_date)
        })
    return data


def generate_industry_benchmarks(config: MockConfig) -> list[dict]:
    """Generate industry benchmark data."""
    data = []
    
    metrics = [
        ("OEE", "World Class", 0.85, "Manufacturing"),
        ("OEE", "Average", 0.60, "Manufacturing"),
        ("First Pass Yield", "World Class", 0.99, "Aerospace"),
        ("First Pass Yield", "Average", 0.95, "Aerospace"),
        ("MTBF", "World Class", 2000, "Industrial Equipment"),
        ("Defect Rate (PPM)", "World Class", 100, "Automotive"),
        ("Defect Rate (PPM)", "Average", 1000, "Automotive"),
        ("On-Time Delivery", "World Class", 0.98, "Supply Chain"),
        ("Inventory Turns", "World Class", 12, "Manufacturing"),
        ("Scrap Rate", "World Class", 0.02, "Manufacturing")
    ]
    
    for i, (metric, level, value, industry) in enumerate(metrics, 1):
        data.append({
            "benchmark_id": i,
            "metric_name": metric,
            "benchmark_level": level,
            "benchmark_value": value,
            "industry_segment": industry,
            "source": random.choice(["Industry Report", "Trade Association", "Research Study"]),
            "year": 2024,
            "created_date": random_datetime(config.start_date, config.end_date)
        })
    return data


def generate_manufacturing_acronyms(config: MockConfig) -> list[dict]:
    """Generate manufacturing acronym reference data."""
    acronyms = [
        ("OEE", "Overall Equipment Effectiveness", "Metrics", "Availability x Performance x Quality"),
        ("MTBF", "Mean Time Between Failures", "Reliability", "Average operating time between failures"),
        ("MTTR", "Mean Time To Repair", "Maintenance", "Average time to repair equipment"),
        ("NCM", "Non-Conformant Material", "Quality", "Material that fails to meet specifications"),
        ("CAPA", "Corrective and Preventive Action", "Quality", "Systematic approach to quality improvement"),
        ("FPY", "First Pass Yield", "Quality", "Percentage passing inspection on first attempt"),
        ("PPM", "Parts Per Million", "Quality", "Defect rate measurement"),
        ("SPC", "Statistical Process Control", "Quality", "Using statistics to monitor production"),
        ("TPM", "Total Productive Maintenance", "Maintenance", "Comprehensive equipment maintenance approach"),
        ("WIP", "Work In Progress", "Production", "Inventory currently being manufactured"),
        ("MRP", "Material Requirements Planning", "Planning", "Production planning and inventory control"),
        ("ERP", "Enterprise Resource Planning", "Systems", "Integrated management of business processes"),
        ("BOM", "Bill of Materials", "Engineering", "List of parts needed for production"),
        ("CAR", "Corrective Action Request", "Quality", "Formal request for corrective action"),
        ("COQ", "Cost of Quality", "Finance", "Total cost of quality-related activities")
    ]
    
    data = []
    for i, (acronym, full_name, category, description) in enumerate(acronyms, 1):
        data.append({
            "acronym_id": i,
            "acronym": acronym,
            "full_name": full_name,
            "category": category,
            "description": description,
            "created_date": random_datetime(config.start_date, config.end_date)
        })
    return data


def generate_users(config: MockConfig) -> list[dict]:
    """Generate user reference data using Faker."""
    fake = config.fake
    data = []
    
    roles = ["Operator", "Supervisor", "Quality Engineer", "Maintenance Tech", 
             "Production Manager", "Quality Manager", "Plant Manager", "Analyst"]
    departments = ["Production", "Quality", "Maintenance", "Engineering", "Planning", "Finance"]
    
    for i in range(1, config.rows_per_table + 1):
        first = fake.first_name()
        last = fake.last_name()
        
        data.append({
            "user_id": i,
            "username": f"{first[0].lower()}{last.lower()}{random.randint(1, 99)}",
            "first_name": first,
            "last_name": last,
            "email": f"{first.lower()}.{last.lower()}@manufacturing.com",
            "role": random.choice(roles),
            "department": random.choice(departments),
            "hire_date": random_date_only(datetime(2015, 1, 1), config.end_date),
            "is_active": random.random() > 0.1,
            "created_date": random_datetime(config.start_date, config.end_date)
        })
    return data


def write_csv(data: list[dict], filepath: Path, preview: bool = False) -> None:
    """Write data to CSV file."""
    if not data:
        return
    
    if preview:
        print(f"\n{filepath.name} ({len(data)} rows):")
        print("-" * 60)
        headers = list(data[0].keys())
        print(",".join(headers))
        for row in data[:3]:
            print(",".join(str(v) for v in row.values()))
        if len(data) > 3:
            print(f"... ({len(data) - 3} more rows)")
        return
    
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
    print(f"  Wrote: {filepath} ({len(data)} rows)")


def generate_all_mock_data(config: MockConfig, preview: bool = False) -> dict[str, list[dict]]:
    """Generate all mock data tables using Faker for realistic synthetic data."""
    random.seed(config.seed)
    output_dir = Path(config.output_dir)
    
    print(f"Generating mock data with Faker (seed={config.seed}, rows={config.rows_per_table})")
    print(f"Date range: {config.start_date.date()} to {config.end_date.date()}")
    print("-" * 70)
    
    # Phase 1: Generate reference tables first
    print("\n[Phase 1] Reference Tables...")
    suppliers = generate_suppliers(config)
    product_lines = generate_product_lines(config)
    production_lines = generate_production_lines(config)
    products = generate_products(config)
    users = generate_users(config)
    manufacturing_acronyms = generate_manufacturing_acronyms(config)
    industry_benchmarks = generate_industry_benchmarks(config)
    
    # Phase 2: Generate transactional data with referential integrity
    print("[Phase 2] Transactional Tables...")
    daily_deliveries = generate_daily_deliveries(config, len(suppliers))
    equipment_metrics = generate_equipment_metrics(config, len(production_lines))
    equipment_count = len(set(row["equipment_id"] for row in equipment_metrics))
    
    product_defects = generate_product_defects(config, len(product_lines))
    failure_events = generate_failure_events(config, equipment_count)
    downtime_events = generate_downtime_events(config, len(production_lines), equipment_count)
    quality_incidents = generate_quality_incidents(config, len(product_lines))
    equipment_reliability = generate_equipment_reliability(config, equipment_count)
    non_conformant_materials = generate_non_conformant_materials(config, len(suppliers), len(product_lines))
    
    # Phase 3: Generate derived/dependent tables
    print("[Phase 3] Derived Tables...")
    production_schedule = generate_production_schedule(config, len(production_lines), len(products))
    production_quality = generate_production_quality(config, len(production_lines))
    corrective_actions = generate_corrective_actions(config, len(quality_incidents))
    effectiveness_metrics = generate_effectiveness_metrics(config, len(corrective_actions))
    quality_costs = generate_quality_costs(config)
    financial_impact = generate_financial_impact(config, len(non_conformant_materials), len(product_defects))
    maintenance_targets = generate_maintenance_targets(config, equipment_count)
    
    all_data = {
        # Reference tables
        "suppliers.csv": suppliers,
        "product_lines.csv": product_lines,
        "production_lines.csv": production_lines,
        "products.csv": products,
        "users.csv": users,
        "manufacturing_acronyms.csv": manufacturing_acronyms,
        "industry_benchmarks.csv": industry_benchmarks,
        # Transactional tables
        "daily_deliveries.csv": daily_deliveries,
        "equipment_metrics.csv": equipment_metrics,
        "equipment_reliability.csv": equipment_reliability,
        "product_defects.csv": product_defects,
        "failure_events.csv": failure_events,
        "downtime_events.csv": downtime_events,
        "quality_incidents.csv": quality_incidents,
        "non_conformant_materials.csv": non_conformant_materials,
        # Derived tables
        "production_schedule.csv": production_schedule,
        "production_quality.csv": production_quality,
        "corrective_actions.csv": corrective_actions,
        "effectiveness_metrics.csv": effectiveness_metrics,
        "quality_costs.csv": quality_costs,
        "financial_impact.csv": financial_impact,
        "maintenance_targets.csv": maintenance_targets,
    }
    
    print("\n[Phase 4] Writing CSV files...")
    for filename, data in all_data.items():
        write_csv(data, output_dir / filename, preview)
    
    print("-" * 70)
    total_rows = sum(len(d) for d in all_data.values())
    print(f"\nGenerated {len(all_data)} tables with {total_rows:,} total rows")
    
    if not preview:
        print(f"\nOutput directory: {output_dir}")
        print("\nNote: Schema metadata tables (schema_nodes, schema_edges, schema_concepts,")
        print("      schema_concept_fields) should be populated from the semantic graph.")
    
    return all_data


def main():
    parser = argparse.ArgumentParser(
        description='Generate mock manufacturing data for SQLMesh Digital Twin'
    )
    parser.add_argument(
        '--rows', '-r',
        type=int,
        default=DEFAULT_ROWS_PER_TABLE,
        help=f'Rows per transactional table (default: {DEFAULT_ROWS_PER_TABLE})'
    )
    parser.add_argument(
        '--output', '-o',
        default='Utilities/SQLMesh/seeds',
        help='Output directory for CSV seeds'
    )
    parser.add_argument(
        '--start-date',
        default='2024-01-01',
        help='Start date for time-series data (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--end-date',
        default='2024-12-31',
        help='End date for time-series data (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--seed', '-s',
        type=int,
        default=42,
        help='Random seed for reproducibility'
    )
    parser.add_argument(
        '--preview', '-p',
        action='store_true',
        help='Preview mode - show sample data without writing files'
    )
    
    args = parser.parse_args()
    
    config = MockConfig(
        start_date=datetime.strptime(args.start_date, "%Y-%m-%d"),
        end_date=datetime.strptime(args.end_date, "%Y-%m-%d"),
        rows_per_table=args.rows,
        output_dir=args.output,
        seed=args.seed
    )
    
    generate_all_mock_data(config, args.preview)
    return 0


if __name__ == '__main__':
    exit(main())
