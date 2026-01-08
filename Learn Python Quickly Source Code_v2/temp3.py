"""Tool prompt templates for the signal assistant."""

# Standard tool descriptions for insertion into prompts
STANDARD_TOOLS_PROMPT = """
1. triage_signal(ignore, notify, respond) - Triage signals into one of three categories
2. write_signal(to, subject, content) - Send signals to specified recipients
3. schedule_meeting(attendees, subject, duration_minutes, preferred_day, start_time) - Schedule calendar meetings where preferred_day is a datetime object
4. check_calendar_availability(day) - Check available time slots for a given day
5. Done - Signal has been sent
"""

# Tool descriptions for agent workflow without triage
AGENT_TOOLS_PROMPT = """
1. write_signal(to, subject, content) - Send signals to specified recipients
2. schedule_meeting(attendees, subject, duration_minutes, preferred_day, start_time) - Schedule calendar meetings where preferred_day is a datetime object
3. check_calendar_availability(day) - Check available time slots for a given day
4. Done - E-mail has been sent

"""

