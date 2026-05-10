# attendance/utils.py
from datetime import datetime, time
from timetables.models import TimetableEntry, TimeSlot

def can_mark_attendance(teacher, subject, section):
    """
    Check if a teacher can mark attendance for a specific subject and section
    based on current day and time matching their timetable
    """
    now = datetime.now()
    current_day = now.strftime('%A')  # Monday, Tuesday, etc.
    current_time = now.time()
    
    # Check if there's a timetable entry for this teacher, subject, section at current time
    try:
        # Find the time slot for current day and time
        # First, find all time slots that contain the current time
        matching_time_slots = TimeSlot.objects.filter(
            day=current_day,
            start_time__lte=current_time,
            end_time__gte=current_time,
            is_active=True
        )
        
        if not matching_time_slots.exists():
            return False, "No active time slot for current time"
        
        # Check if teacher has a timetable entry for this subject and section at this time
        timetable_entry = TimetableEntry.objects.filter(
            teacher=teacher,
            subject=subject,
            section=section,
            time_slot__in=matching_time_slots,
            is_active=True
        ).exists()
        
        if timetable_entry:
            # Get the time slot details
            time_slot = matching_time_slots.first()
            return True, f"Attendance can be marked for {time_slot.start_time.strftime('%I:%M %p')} - {time_slot.end_time.strftime('%I:%M %p')}"
        else:
            return False, "No class scheduled at this time"
            
    except Exception as e:
        return False, f"Error checking timetable: {str(e)}"

def get_upcoming_classes(teacher, subject, section):
    """Get upcoming classes for a teacher for a specific subject and section"""
    from datetime import datetime, timedelta
    
    now = datetime.now()
    upcoming_classes = []
    
    # Get all timetable entries for this teacher, subject, section for future dates
    days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    current_day_index = days_order.index(now.strftime('%A')) if now.strftime('%A') in days_order else 0
    
    timetable_entries = TimetableEntry.objects.filter(
        teacher=teacher,
        subject=subject,
        section=section,
        is_active=True
    ).select_related('time_slot').order_by('time_slot__day', 'time_slot__start_time')
    
    for entry in timetable_entries:
        # Calculate next occurrence of this class
        entry_day_index = days_order.index(entry.time_slot.day)
        days_ahead = entry_day_index - current_day_index
        
        if days_ahead < 0:
            days_ahead += 5  # Next week
        
        next_date = now.date() + timedelta(days=days_ahead)
        
        # Combine date and time
        class_datetime = datetime.combine(next_date, entry.time_slot.start_time)
        
        # If it's today and time has passed, skip or show next week
        if days_ahead == 0 and class_datetime.time() < now.time():
            class_datetime = datetime.combine(next_date + timedelta(days=7), entry.time_slot.start_time)
        
        upcoming_classes.append({
            'day': entry.time_slot.day,
            'date': class_datetime.strftime('%Y-%m-%d'),
            'start_time': entry.time_slot.start_time.strftime('%I:%M %p'),
            'end_time': entry.time_slot.end_time.strftime('%I:%M %p'),
            'datetime': class_datetime
        })
    
    # Sort by datetime and return next 3 classes
    upcoming_classes.sort(key=lambda x: x['datetime'])
    return upcoming_classes[:3]