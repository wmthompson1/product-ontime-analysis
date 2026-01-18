"""
025 - Mock Data Generator for Manufacturing Digital Twin (Part 2)
=================================================================
Generates realistic mock data for the manufacturing schema to populate
the SQLMesh staging models. Creates DuckDB-compatible seed data.

Usage:
    python 025_Entry_Point_DDL_to_SQLMesh_Part2.py [--rows N] [--output-dir PATH] [--preview]

Features:
    - Generates realistic manufacturing metrics (OEE, MTBF, defect rates)
    - Maintains referential integrity across tables
    - Creates time-series data with configurable date ranges
    - Outputs CSV seeds for SQLMesh SEED models
"""

import os
import csv
import random
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Optional


# Configuration
DEFAULT_START_DATE = datetime(2024, 1, 1)
DEFAULT_END_DATE = datetime(2024, 12, 31)
DEFAULT_ROWS_PER_TABLE = 100


@dataclass
class MockConfig:
    """Configuration for mock data generation."""
    start_date: datetime = DEFAULT_START_DATE
    end_date: datetime = DEFAULT_END_DATE
    rows_per_table: int = DEFAULT_ROWS_PER_TABLE
    output_dir: str = "Utilities/SQLMesh/seeds"
    seed: int = 42


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
    """Generate supplier reference data."""
    data = []
    for i, (name, email, phone, address) in enumerate(SUPPLIERS, 1):
        data.append({
            "supplier_id": i,
            "supplier_name": name,
            "contact_email": email,
            "phone": phone,
            "address": address,
            "performance_rating": round(random.uniform(3.5, 5.0), 2),
            "certification_level": random.choice(["AS9100", "ISO9001", "IATF16949", "ISO13485"]),
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
    """Generate production line reference data."""
    data = []
    supervisors = ["John Smith", "Maria Garcia", "Wei Chen", "James Johnson", "Sarah Williams", "Ahmed Hassan"]
    for i, (name, location, line_type, capacity) in enumerate(PRODUCTION_LINES, 1):
        actual_cap = int(capacity * random.uniform(0.7, 0.95))
        data.append({
            "line_id": i,
            "line_name": name,
            "facility_location": location,
            "line_type": line_type,
            "theoretical_capacity": capacity,
            "actual_capacity": actual_cap,
            "efficiency_rating": round(actual_cap / capacity * 100, 1),
            "installation_date": random_date_only(datetime(2015, 1, 1), datetime(2022, 12, 31)),
            "last_maintenance_date": random_date_only(config.start_date, config.end_date),
            "status": random.choice(["Active", "Active", "Active", "Maintenance", "Idle"]),
            "supervisor": random.choice(supervisors),
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
    """Generate all mock data tables."""
    random.seed(config.seed)
    output_dir = Path(config.output_dir)
    
    print(f"Generating mock data (seed={config.seed}, rows={config.rows_per_table})")
    print(f"Date range: {config.start_date.date()} to {config.end_date.date()}")
    print("-" * 60)
    
    # Generate reference tables first
    suppliers = generate_suppliers(config)
    product_lines = generate_product_lines(config)
    production_lines = generate_production_lines(config)
    
    # Generate transactional data with referential integrity
    daily_deliveries = generate_daily_deliveries(config, len(suppliers))
    equipment_metrics = generate_equipment_metrics(config, len(production_lines))
    equipment_count = len(set(row["equipment_id"] for row in equipment_metrics))
    
    product_defects = generate_product_defects(config, len(product_lines))
    failure_events = generate_failure_events(config, equipment_count)
    downtime_events = generate_downtime_events(config, len(production_lines), equipment_count)
    quality_incidents = generate_quality_incidents(config, len(product_lines))
    equipment_reliability = generate_equipment_reliability(config, equipment_count)
    
    all_data = {
        "suppliers.csv": suppliers,
        "product_lines.csv": product_lines,
        "production_lines.csv": production_lines,
        "daily_deliveries.csv": daily_deliveries,
        "equipment_metrics.csv": equipment_metrics,
        "equipment_reliability.csv": equipment_reliability,
        "product_defects.csv": product_defects,
        "failure_events.csv": failure_events,
        "downtime_events.csv": downtime_events,
        "quality_incidents.csv": quality_incidents,
    }
    
    for filename, data in all_data.items():
        write_csv(data, output_dir / filename, preview)
    
    print("-" * 60)
    total_rows = sum(len(d) for d in all_data.values())
    print(f"Generated {len(all_data)} tables with {total_rows:,} total rows")
    
    if not preview:
        print(f"\nOutput directory: {output_dir}")
        print("\nTo use with SQLMesh, create SEED models referencing these CSVs.")
    
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
