from decimal import Decimal
from django.utils import timezone
from student.models import Student
from teachers.models import Teacher
from subject.models import Subject, SubjectAssign
from Academic.models import Batch, Semester, Section, Discipline
from exam_manag.models import Exam, ExamResult, StudentSubjectResult, ComprehensiveResult

def create_demo_subjects():
    """Create demo subjects"""
    subjects_data = [
        {'code': 'DEMO101', 'name': 'Introduction to Computer Science', 'credit_hours': 3},
        {'code': 'DEMO102', 'name': 'Programming Fundamentals', 'credit_hours': 3},
        {'code': 'DEMO103', 'name': 'Database Management', 'credit_hours': 3},
    ]
    
    created = []
    for data in subjects_data:
        subject, created_flag = Subject.objects.get_or_create(
            code=data['code'],
            defaults={
                'name': data['name'],
                'credit_hours': data['credit_hours'],
                'subject_type': 'core',
            }
        )
        created.append(subject.code)
        print(f"✅ Demo Subject: {subject.code} - {subject.name}")
    
    return created

def create_demo_assignments(teacher, subject, section):
    """Create demo assignments"""
    from assignm.models import Assignment
    
    assignments_data = [
        {'title': 'Assignment 1: Basic Concepts', 'total_marks': 10},
        {'title': 'Assignment 2: Practical Exercise', 'total_marks': 20},
        {'title': 'Quiz 1', 'total_marks': 5},
    ]
    
    created = []
    for data in assignments_data:
        assignment, created_flag = Assignment.objects.get_or_create(
            title=data['title'],
            subject_assign__subject=subject,
            teacher=teacher,
            defaults={
                'description': f'Demo {data["title"]} for testing',
                'total_marks': data['total_marks'],
                'due_date': timezone.now() + timezone.timedelta(days=7),
                'is_active': True,
            }
        )
        if created_flag:
            assignment.sections.add(section)
            created.append(assignment.title)
            print(f"✅ Demo Assignment: {assignment.title}")
    
    return created

def create_demo_attendance(student, subject, section):
    """Create demo attendance records"""
    from attendance.models import Attendance
    
    # Create last 5 days attendance
    for i in range(5):
        date = timezone.now().date() - timezone.timedelta(days=i)
        attendance, created = Attendance.objects.get_or_create(
            student=student,
            subject=subject,
            date=date,
            defaults={
                'status': 'Present',
                'section': section,
            }
        )
        if created:
            print(f"✅ Demo Attendance: {student.first_name} - {date}")
    
    return True

def create_demo_marks(teacher, student, subject, section):
    """Create demo exam marks"""
    from exam_manag.models import Exam, ExamResult
    
    exam_types = [
        {'type': 'mid_term', 'name': 'Mid Term', 'marks': 16, 'total': 20},
        {'type': 'final', 'name': 'Final', 'marks': 40, 'total': 50},
        {'type': 'quiz', 'name': 'Quiz', 'marks': 4, 'total': 5},
        {'type': 'assignment', 'name': 'Assignment', 'marks': 4, 'total': 5},
        {'type': 'lab', 'name': 'Lab', 'marks': 12, 'total': 15},
        {'type': 'attendance', 'name': 'Attendance', 'marks': 4, 'total': 5},
    ]
    
    for exam_data in exam_types:
        # Create exam
        exam, created = Exam.objects.get_or_create(
            subject=subject,
            section=section,
            exam_type=exam_data['type'],
            defaults={
                'total_marks': exam_data['total'],
                'teacher': teacher,
                'is_published': True,
            }
        )
        
        # Create exam result
        result, created = ExamResult.objects.get_or_create(
            exam=exam,
            student=student,
            defaults={
                'marks_obtained': Decimal(str(exam_data['marks'])),
                'entered_by': teacher,
            }
        )
        print(f"✅ Demo Marks: {subject.code} - {exam_data['name']}: {exam_data['marks']}/{exam_data['total']}")
    
    return True

def setup_all_demo_data():
    """Setup all demo data at once"""
    print("\n" + "="*60)
    print("SETTING UP DEMO DATA")
    print("="*60)
    
    # Get demo user
    from home_auth.models import CustomUser
    demo_user = CustomUser.objects.get(username='demo_user')
    teacher = Teacher.objects.get(user=demo_user)
    student = Student.objects.get(user=demo_user)
    section = Section.objects.get(name='Demo Section A')
    
    # Create subjects
    subjects = create_demo_subjects()
    
    # For each subject, create data
    for subject_code in subjects:
        subject = Subject.objects.get(code=subject_code)
        
        # Create assignment
        create_demo_assignments(teacher, subject, section)
        
        # Create attendance
        create_demo_attendance(student, subject, section)
        
        # Create marks
        create_demo_marks(teacher, student, subject, section)
    
    print("\n" + "="*60)
    print("✅ ALL DEMO DATA CREATED!")
    print("="*60)
    
    return True

# Run this function
if __name__ == "__main__":
    setup_all_demo_data()