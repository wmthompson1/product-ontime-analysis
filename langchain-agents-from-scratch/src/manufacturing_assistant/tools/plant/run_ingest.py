#manufacturing_assistant/tools/plant/run_ingest.py
import re
import json
import logging

# Configure basic logging for the ingestion process itself
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class LogIngestor:
    def __init__(self, log_file_path):
        self.log_file_path = log_file_path
        self.parsed_errors = []

    def read_logs(self):
        """Reads the log file line by line."""
        try:
            with open(self.log_file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    yield line.strip()
        except FileNotFoundError:
            logging.error(f"Log file not found at: {self.log_file_path}")
            return
        except Exception as e:
            logging.error(f"Error reading log file: {e}")
            return

    def parse_log_line(self, log_line):
        """Parses a single log line to extract error information.
        This is a placeholder and needs to be adapted to your log format.
        """
        # Example: Simple regex to extract timestamp, level, and message
        match = re.match(r'\[(.*?)\] (ERROR|WARN|INFO): (.*)', log_line)
        if match:
            timestamp, level, message = match.groups()
            return {
                'timestamp': timestamp,
                'level': level,
                'message': message,
                'raw_line': log_line
            }
        # Example for JSON logs
        try:
            json_data = json.loads(log_line)
            if json_data.get('level') == 'ERROR':
                return {
                    'timestamp': json_data.get('timestamp'),
                    'level': json_data.get('level'),
                    'message': json_data.get('message'),
                    'raw_line': log_line
                }
        except json.JSONDecodeError:
            pass # Not a JSON log line

        return None # Could not parse

    def ingest_errors(self):
        """Ingests and parses all error logs from the file."""
        for line in self.read_logs():
            parsed_data = self.parse_log_line(line)
            if parsed_data and parsed_data['level'] == 'ERROR':
                self.parsed_errors.append(parsed_data)
                logging.info(f"Ingested error: {parsed_data['message']}")
        return self.parsed_errors

    def get_ingested_errors(self):
        """Returns the list of parsed error logs."""
        return self.parsed_errors

# Example Usage:
if __name__ == "__main__":
    # Create a dummy log file for demonstration
    with open("example_error.log", "w") as f:
        f.write("[2025-09-01 12:00:00] INFO: Application started\n")
        f.write("[2025-09-01 12:01:15] ERROR: Database connection failed: Connection refused\n")
        f.write("[2025-09-01 12:02:30] WARN: Low disk space warning\n")
        f.write('{"timestamp": "2025-09-01 12:03:45", "level": "ERROR", "message": "API timeout during user login"}\n')
        f.write("[2025-09-01 12:04:00] ERROR: Unhandled exception in main loop\n")

    ingestor = LogIngestor("example_error.log")
    errors = ingestor.ingest_errors()

    print("\n--- Ingested Errors ---")
    for error in errors:
        print(json.dumps(error, indent=2))

    # In a real agentic AI system, 'errors' would then be passed to an agent
    # for analysis, action, or knowledge base updates.
    # For example, an agent could:
    # - Analyze error patterns
    # - Trigger alerts
    # - Attempt automated remediation
    # - Update a knowledge base of known issues and solutions