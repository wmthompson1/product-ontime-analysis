#!/usr/bin/env python3
"""
017_Entry_Point_Manufacturing_Plant_Ingest.py
Manufacturing Plant Log Data Ingestion Script
Adapted from Gmail ingestion for plant operations data processing
"""

import os
import json
import uuid
import hashlib
import asyncio
import argparse
from pathlib import Path
from datetime import datetime, timedelta
import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import logging

# Manufacturing log parsing imports
import csv
from collections import defaultdict

# LangChain imports (optional for demo)
try:
    from langchain_core.messages import HumanMessage
    from langchain_openai import ChatOpenAI
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    print("LangChain not available - running without AI recommendations")


@dataclass
class PlantLogEntry:
    """Manufacturing plant log entry structure"""
    timestamp: datetime
    equipment_id: str
    log_level: str  # INFO, WARNING, ERROR, CRITICAL
    message: str
    source_file: str
    line_number: int
    raw_data: str
    metadata: Dict[str, Any]


@dataclass
class ManufacturingAlert:
    """Manufacturing alert derived from log analysis"""
    alert_id: str
    equipment_id: str
    alert_type: str  # equipment_failure, quality_issue, maintenance_required
    severity: str  # critical, high, medium, low
    description: str
    timestamp: datetime
    log_entries: List[PlantLogEntry]
    recommended_actions: List[str]


class ManufacturingLogParser:
    """Parse manufacturing plant log files into structured data"""

    def __init__(self):
        self.equipment_patterns = {
            'CNC': r'CNC-\d+',
            'PRESS': r'PRESS-\d+',
            'ROBOT': r'ROBOT-\d+',
            'LINE': r'LINE-[A-Z]',
            'CONVEYOR': r'CONV-\d+',
            'QUALITY': r'QC-\d+'
        }

        self.alert_patterns = {
            'equipment_failure': [
                r'fault|error|failure|malfunction|down|stopped',
                r'emergency stop|e-stop|alarm',
                r'motor fault|sensor error|hydraulic failure'
            ],
            'quality_issue': [
                r'defect|quality|tolerance|specification',
                r'out of spec|reject|scrap',
                r'dimensional error|surface finish'
            ],
            'maintenance_required': [
                r'maintenance|service|lubrication|calibration',
                r'wear|replace|inspect|clean', r'schedule|due|overdue'
            ]
        }

    def parse_log_line(self, line: str, source_file: str,
                       line_number: int) -> Optional[PlantLogEntry]:
        """Parse a single log line into structured format"""
        try:
            # Common log format: TIMESTAMP [LEVEL] EQUIPMENT_ID: MESSAGE
            log_pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+\[(\w+)\]\s+([A-Z-0-9]+):\s+(.*)'
            match = re.match(log_pattern, line.strip())

            if match:
                timestamp_str, level, equipment_id, message = match.groups()
                timestamp = datetime.strptime(timestamp_str,
                                              '%Y-%m-%d %H:%M:%S')

                # Extract metadata from message
                metadata = self._extract_metadata(message)

                return PlantLogEntry(timestamp=timestamp,
                                     equipment_id=equipment_id,
                                     log_level=level,
                                     message=message,
                                     source_file=source_file,
                                     line_number=line_number,
                                     raw_data=line.strip(),
                                     metadata=metadata)

            return None

        except Exception as e:
            logging.warning(f"Failed to parse log line {line_number}: {e}")
            return None

    def _extract_metadata(self, message: str) -> Dict[str, Any]:
        """Extract structured metadata from log message"""
        metadata = {}

        # Extract numeric values
        temp_match = re.search(r'temperature[:\s]+(\d+\.?\d*)',
                               message.lower())
        if temp_match:
            metadata['temperature'] = float(temp_match.group(1))

        pressure_match = re.search(r'pressure[:\s]+(\d+\.?\d*)',
                                   message.lower())
        if pressure_match:
            metadata['pressure'] = float(pressure_match.group(1))

        speed_match = re.search(r'speed[:\s]+(\d+\.?\d*)', message.lower())
        if speed_match:
            metadata['speed'] = float(speed_match.group(1))

        # Extract status indicators
        if re.search(r'running|operational|normal', message.lower()):
            metadata['status'] = 'operational'
        elif re.search(r'stopped|down|offline', message.lower()):
            metadata['status'] = 'down'
        elif re.search(r'warning|caution', message.lower()):
            metadata['status'] = 'warning'

        return metadata

    def parse_log_file(self, file_path: Path) -> List[PlantLogEntry]:
        """Parse entire log file into structured entries"""
        entries = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    entry = self.parse_log_line(line, str(file_path), line_num)
                    if entry:
                        entries.append(entry)

            logging.info(f"Parsed {len(entries)} entries from {file_path}")
            return entries

        except Exception as e:
            logging.error(f"Failed to parse log file {file_path}: {e}")
            return []


class ManufacturingAlertGenerator:
    """Generate manufacturing alerts from parsed log entries"""

    def __init__(self):
        if LANGCHAIN_AVAILABLE:
            self.llm = ChatOpenAI(model="gpt-4o-2024-08-06", temperature=0.0)
        else:
            self.llm = None

    def analyze_log_entries(
            self, entries: List[PlantLogEntry]) -> List[ManufacturingAlert]:
        """Analyze log entries and generate alerts"""
        alerts = []

        # Group entries by equipment
        equipment_logs = defaultdict(list)
        for entry in entries:
            equipment_logs[entry.equipment_id].append(entry)

        # Analyze each equipment's logs
        for equipment_id, logs in equipment_logs.items():
            equipment_alerts = self._analyze_equipment_logs(equipment_id, logs)
            alerts.extend(equipment_alerts)

        return alerts

    def _analyze_equipment_logs(
            self, equipment_id: str,
            logs: List[PlantLogEntry]) -> List[ManufacturingAlert]:
        """Analyze logs for specific equipment"""
        alerts = []

        # Check for error patterns
        error_logs = [
            log for log in logs if log.log_level in ['ERROR', 'CRITICAL']
        ]
        if error_logs:
            alert = self._create_equipment_failure_alert(
                equipment_id, error_logs)
            if alert:
                alerts.append(alert)

        # Check for maintenance patterns
        maintenance_logs = [
            log for log in logs if 'maintenance' in log.message.lower()
        ]
        if maintenance_logs:
            alert = self._create_maintenance_alert(equipment_id,
                                                   maintenance_logs)
            if alert:
                alerts.append(alert)

        # Check for quality issues
        quality_logs = [
            log for log in logs
            if any(term in log.message.lower()
                   for term in ['defect', 'quality', 'tolerance', 'spec'])
        ]
        if quality_logs:
            alert = self._create_quality_alert(equipment_id, quality_logs)
            if alert:
                alerts.append(alert)

        return alerts

    def _create_equipment_failure_alert(
            self, equipment_id: str,
            error_logs: List[PlantLogEntry]) -> Optional[ManufacturingAlert]:
        """Create equipment failure alert"""
        if not error_logs:
            return None

        latest_error = max(error_logs, key=lambda x: x.timestamp)

        # Use LLM to generate recommended actions
        log_summary = "\n".join(
            [f"{log.timestamp}: {log.message}" for log in error_logs[-3:]])

        prompt = f"""
        Equipment {equipment_id} is experiencing failures. Recent error logs:
        
        {log_summary}
        
        Provide 3 specific recommended actions for this equipment failure.
        """

        if self.llm and LANGCHAIN_AVAILABLE:
            try:
                response = self.llm.invoke([HumanMessage(content=prompt)])
                recommended_actions = response.content.strip().split('\n')
                recommended_actions = [
                    action.strip('- ').strip()
                    for action in recommended_actions if action.strip()
                ]
            except:
                recommended_actions = [
                    f"Inspect {equipment_id} for mechanical issues",
                    f"Check {equipment_id} sensor connections",
                    f"Review {equipment_id} maintenance logs"
                ]
        else:
            recommended_actions = [
                f"Inspect {equipment_id} for mechanical issues",
                f"Check {equipment_id} sensor connections",
                f"Review {equipment_id} maintenance logs"
            ]

        return ManufacturingAlert(
            alert_id=str(uuid.uuid4())[:8],
            equipment_id=equipment_id,
            alert_type='equipment_failure',
            severity='critical'
            if latest_error.log_level == 'CRITICAL' else 'high',
            description=
            f"Equipment failure detected in {equipment_id}: {latest_error.message}",
            timestamp=latest_error.timestamp,
            log_entries=error_logs,
            recommended_actions=recommended_actions)

    def _create_maintenance_alert(
            self, equipment_id: str, maintenance_logs: List[PlantLogEntry]
    ) -> Optional[ManufacturingAlert]:
        """Create maintenance alert"""
        if not maintenance_logs:
            return None

        latest_log = max(maintenance_logs, key=lambda x: x.timestamp)

        return ManufacturingAlert(
            alert_id=str(uuid.uuid4())[:8],
            equipment_id=equipment_id,
            alert_type='maintenance_required',
            severity='medium',
            description=
            f"Maintenance required for {equipment_id}: {latest_log.message}",
            timestamp=latest_log.timestamp,
            log_entries=maintenance_logs,
            recommended_actions=[
                f"Schedule maintenance for {equipment_id}",
                f"Check {equipment_id} maintenance schedule",
                f"Prepare maintenance tools and parts"
            ])

    def _create_quality_alert(
            self, equipment_id: str,
            quality_logs: List[PlantLogEntry]) -> Optional[ManufacturingAlert]:
        """Create quality alert"""
        if not quality_logs:
            return None

        latest_log = max(quality_logs, key=lambda x: x.timestamp)

        return ManufacturingAlert(
            alert_id=str(uuid.uuid4())[:8],
            equipment_id=equipment_id,
            alert_type='quality_issue',
            severity='high',
            description=
            f"Quality issue detected in {equipment_id}: {latest_log.message}",
            timestamp=latest_log.timestamp,
            log_entries=quality_logs,
            recommended_actions=[
                f"Inspect {equipment_id} output quality",
                f"Calibrate {equipment_id} quality sensors",
                f"Review {equipment_id} quality control procedures"
            ])


class ManufacturingPlantIngestion:
    """Main ingestion class for manufacturing plant data"""

    def __init__(self, log_directory: str = "./sample_data"):
        self.log_directory = Path(log_directory)
        self.parser = ManufacturingLogParser()
        self.alert_generator = ManufacturingAlertGenerator()

        # Setup logging
        logging.basicConfig(level=logging.INFO,
                            format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)

    def create_sample_log_files(self):
        """Create sample manufacturing log files for demonstration"""
        self.log_directory.mkdir(exist_ok=True)

        # Sample log data for different equipment
        sample_logs = {
            'cnc_001.log': [
                '2025-09-01 08:00:15 [INFO] CNC-001: Starting machining operation',
                '2025-09-01 08:15:30 [WARNING] CNC-001: Tool wear detected, replace soon',
                '2025-09-01 08:45:22 [ERROR] CNC-001: Spindle motor fault detected',
                '2025-09-01 09:00:45 [CRITICAL] CNC-001: Emergency stop activated due to coolant leak',
                '2025-09-01 09:30:15 [INFO] CNC-001: Maintenance team dispatched',
                '2025-09-01 10:15:30 [ERROR] CNC-001: Chuck jaws failed to close properly',
                '2025-09-01 11:22:45 [ERROR] CNC-001: Axis servo drive communication error',
                '2025-09-01 12:30:20 [WARNING] CNC-001: Coolant level low, refill required',
                '2025-09-01 13:45:10 [ERROR] CNC-001: Tool changer mechanism jammed',
                '2025-09-01 14:20:35 [ERROR] CNC-001: Program execution halted - invalid G-code',
            ],
            'press_002.log': [
                '2025-09-01 07:30:10 [INFO] PRESS-002: Hydraulic press operational',
                '2025-09-01 10:15:45 [WARNING] PRESS-002: Pressure reading 850 PSI, above normal range',
                '2025-09-01 11:30:20 [INFO] PRESS-002: Quality check - 3 defective parts detected',
                '2025-09-01 12:45:30 [ERROR] PRESS-002: Hydraulic pump failure',
                '2025-09-01 13:00:15 [INFO] PRESS-002: Maintenance scheduled for hydraulic system',
                '2025-09-01 14:15:45 [ERROR] PRESS-002: Safety light curtain breach detected',
                '2025-09-01 15:30:20 [ERROR] PRESS-002: Die alignment sensor malfunction',
                '2025-09-01 16:22:10 [WARNING] PRESS-002: Oil temperature exceeding limits',
                '2025-09-01 17:05:55 [ERROR] PRESS-002: Pressure relief valve stuck open',
                '2025-09-01 18:10:30 [ERROR] PRESS-002: Ram position encoder failure',
            ],
            'robot_003.log': [
                '2025-09-01 06:00:00 [INFO] ROBOT-003: Robotic arm initialized',
                '2025-09-01 08:30:25 [INFO] ROBOT-003: Pick and place cycle completed - 1247 parts',
                '2025-09-01 10:45:15 [WARNING] ROBOT-003: Joint 3 temperature 75°C, approaching limit',
                '2025-09-01 12:15:40 [INFO] ROBOT-003: Calibration check passed',
                '2025-09-01 14:30:55 [WARNING] ROBOT-003: Gripper force sensor out of tolerance',
                '2025-09-01 15:45:20 [ERROR] ROBOT-003: End effector collision detected',
                '2025-09-01 16:20:10 [ERROR] ROBOT-003: Joint 2 servo motor overcurrent fault',
                '2025-09-01 17:35:45 [WARNING] ROBOT-003: Vision system calibration drift',
                '2025-09-01 18:22:30 [ERROR] ROBOT-003: Emergency stop triggered by safety scanner',
                '2025-09-01 19:10:15 [ERROR] ROBOT-003: Communication timeout with controller',
            ],
            'line_a.log': [
                '2025-09-01 06:30:00 [INFO] LINE-A: Production line startup complete',
                '2025-09-01 09:15:30 [INFO] LINE-A: Throughput rate 95 units/hour',
                '2025-09-01 11:45:20 [WARNING] LINE-A: Conveyor speed reduced due to quality issues',
                '2025-09-01 13:30:10 [ERROR] LINE-A: Station 3 sensor malfunction',
                '2025-09-01 15:00:45 [INFO] LINE-A: Quality inspection - 2% defect rate',
                '2025-09-01 16:15:25 [ERROR] LINE-A: Conveyor belt tracking error detected',
                '2025-09-01 17:22:40 [ERROR] LINE-A: Parts feeder bowl vibration motor failure',
                '2025-09-01 18:35:15 [WARNING] LINE-A: Reject bin approaching capacity',
                '2025-09-01 19:42:30 [ERROR] LINE-A: Barcode scanner unable to read labels',
                '2025-09-01 20:15:55 [ERROR] LINE-A: PLC communication error with HMI station',
            ],
            'quality_control.log': [
                '2025-09-01 08:00:00 [INFO] QC-001: Quality control system startup',
                '2025-09-01 09:30:15 [WARNING] QC-001: Dimensional variance exceeding tolerance',
                '2025-09-01 10:45:30 [ERROR] QC-001: CMM probe calibration failed',
                '2025-09-01 11:20:45 [ERROR] QC-001: Surface roughness measurement out of range',
                '2025-09-01 12:35:20 [INFO] QC-001: Batch inspection completed - 15 rejects',
                '2025-09-01 13:50:10 [ERROR] QC-001: Optical inspection camera focus error',
                '2025-09-01 15:15:25 [ERROR] QC-001: Torque tester communication failure',
                '2025-09-01 16:30:40 [WARNING] QC-001: Statistical process control limits exceeded',
                '2025-09-01 17:45:55 [ERROR] QC-001: Hardness tester indenter worn beyond limits',
                '2025-09-01 19:00:20 [ERROR] QC-001: Go/No-Go gauge pneumatic system leak',
            ]
        }

        for filename, logs in sample_logs.items():
            log_file = self.log_directory / filename
            with open(log_file, 'w') as f:
                f.write('\n'.join(logs) + '\n')

        self.logger.info(
            f"Created {len(sample_logs)} sample log files in {self.log_directory}"
        )

    def ingest_log_files(self,
                         pattern: str = "*.log") -> List[ManufacturingAlert]:
        """Ingest all log files matching pattern"""
        all_entries = []

        # Find all log files
        log_files = list(self.log_directory.glob(pattern))
        if not log_files:
            self.logger.warning(
                f"No log files found in {self.log_directory} matching {pattern}"
            )
            return []

        self.logger.info(f"Found {len(log_files)} log files to process")

        # Parse each log file
        for log_file in log_files:
            self.logger.info(f"Processing {log_file}")
            entries = self.parser.parse_log_file(log_file)
            all_entries.extend(entries)

        self.logger.info(f"Parsed total of {len(all_entries)} log entries")

        # Generate alerts from parsed entries
        alerts = self.alert_generator.analyze_log_entries(all_entries)
        self.logger.info(f"Generated {len(alerts)} manufacturing alerts")

        return alerts

    def save_alerts_to_json(self,
                            alerts: List[ManufacturingAlert],
                            output_file: str = "manufacturing_alerts.json"):
        """Save generated alerts to JSON file"""
        alert_data = []

        for alert in alerts:
            alert_dict = {
                'alert_id': alert.alert_id,
                'equipment_id': alert.equipment_id,
                'alert_type': alert.alert_type,
                'severity': alert.severity,
                'description': alert.description,
                'timestamp': alert.timestamp.isoformat(),
                'recommended_actions': alert.recommended_actions,
                'log_entries_count': len(alert.log_entries)
            }
            alert_data.append(alert_dict)

        with open(output_file, 'w') as f:
            json.dump(alert_data, f, indent=2)

        self.logger.info(f"Saved {len(alerts)} alerts to {output_file}")

    def generate_summary_report(self, alerts: List[ManufacturingAlert]) -> str:
        """Generate summary report of manufacturing alerts"""
        if not alerts:
            return "No manufacturing alerts generated."

        # Group alerts by type and severity
        alert_by_type = defaultdict(int)
        alert_by_severity = defaultdict(int)
        equipment_alerts = defaultdict(int)

        for alert in alerts:
            alert_by_type[alert.alert_type] += 1
            alert_by_severity[alert.severity] += 1
            equipment_alerts[alert.equipment_id] += 1

        report = []
        report.append("MANUFACTURING PLANT INGESTION SUMMARY REPORT")
        report.append("=" * 50)
        report.append(f"Total Alerts Generated: {len(alerts)}")
        report.append(
            f"Analysis Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")

        report.append("ALERTS BY TYPE:")
        for alert_type, count in alert_by_type.items():
            report.append(f"  {alert_type.replace('_', ' ').title()}: {count}")
        report.append("")

        report.append("ALERTS BY SEVERITY:")
        for severity, count in alert_by_severity.items():
            report.append(f"  {severity.title()}: {count}")
        report.append("")

        report.append("EQUIPMENT WITH ALERTS:")
        for equipment, count in equipment_alerts.items():
            report.append(f"  {equipment}: {count} alerts")
        report.append("")

        report.append("RECENT CRITICAL ALERTS:")
        critical_alerts = [a for a in alerts if a.severity == 'critical']
        for alert in critical_alerts[:5]:  # Show top 5 critical alerts
            report.append(f"  {alert.equipment_id}: {alert.description}")

        return "\n".join(report)


def demo_manufacturing_plant_ingestion():
    """Demonstrate the manufacturing plant ingestion system"""
    print("🏭 Manufacturing Plant Log Ingestion Demo")
    print("Adapted from Gmail ingestion for plant operations")
    print("=" * 60)

    # Initialize ingestion system
    ingestion = ManufacturingPlantIngestion()

    # Create sample log files
    print("\n📁 Creating sample manufacturing log files...")
    ingestion.create_sample_log_files()

    # Process log files
    print("\n🔄 Processing manufacturing log files...")
    alerts = ingestion.ingest_log_files()

    # Display results
    print(f"\n📊 Processing Complete - Generated {len(alerts)} alerts")

    if alerts:
        print("\n🚨 Manufacturing Alerts Generated:")
        print("-" * 40)

        for alert in alerts:
            severity_icon = {
                'critical': '🔴',
                'high': '🟠',
                'medium': '🟡',
                'low': '🟢'
            }.get(alert.severity, '⚪')

            print(f"{severity_icon} {alert.alert_id}: {alert.equipment_id}")
            print(f"   Type: {alert.alert_type.replace('_', ' ').title()}")
            print(f"   Severity: {alert.severity.title()}")
            print(f"   Description: {alert.description}")
            print(f"   Actions: {', '.join(alert.recommended_actions[:2])}...")
            print()

        # Save alerts to JSON
        print("💾 Saving alerts to JSON file...")
        ingestion.save_alerts_to_json(alerts)

        # Generate summary report
        print("\n📋 Summary Report:")
        print("-" * 40)
        summary = ingestion.generate_summary_report(alerts)
        print(summary)

    print("\n" + "=" * 60)
    print("🎯 Manufacturing Plant Ingestion Complete!")
    print("📧➡️🏭 Gmail ingestion adapted for plant operations")
    print("📊 Log files processed and alerts generated")
    print("📚 Ready for Berkeley Haas capstone deployment")


if __name__ == "__main__":
    # Setup argument parser
    parser = argparse.ArgumentParser(
        description="Manufacturing Plant Log Ingestion")
    parser.add_argument("--log-dir",
                        default="./sample_data",
                        help="Directory containing log files")
    parser.add_argument("--pattern",
                        default="*.log",
                        help="File pattern to match")
    parser.add_argument("--output",
                        default="manufacturing_alerts.json",
                        help="Output file for alerts")
    parser.add_argument("--demo",
                        action="store_true",
                        help="Run demonstration with sample data")

    args = parser.parse_args()

    if args.demo:
        # Run the demonstration
        demo_manufacturing_plant_ingestion()
    else:
        # Run with custom parameters
        ingestion = ManufacturingPlantIngestion(args.log_dir)
        alerts = ingestion.ingest_log_files(args.pattern)
        ingestion.save_alerts_to_json(alerts, args.output)
        summary = ingestion.generate_summary_report(alerts)
        print(summary)
