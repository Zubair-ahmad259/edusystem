# populate_passwords.py
import os
import django
import random
import string

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'home.settings')
django.setup()

from home_auth.models import CustomUser
from student.models import Student
from teachers.models import Teacher
from head.models import AdminProfile

def generate_random_password():
    """Generate a random 10-character password"""
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(10))

def populate_student_passwords():
    """Populate temp_passwords for students"""
    students = Student.objects.filter(user__isnull=False)
    count = 0
    
    for student in students:
        if student.user and not student.user.temp_password:
            new_password = generate_random_password()
            student.user.temp_password = new_password
            student.user.save()
            print(f"Student: {student.name or student.email} -> Password: {new_password}")
            count += 1
    
    return count

def populate_teacher_passwords():
    """Populate temp_passwords for teachers"""
    teachers = Teacher.objects.filter(user__isnull=False)
    count = 0
    
    for teacher in teachers:
        if teacher.user and not teacher.user.temp_password:
            new_password = generate_random_password()
            teacher.user.temp_password = new_password
            teacher.user.save()
            print(f"Teacher: {teacher.name or teacher.email} -> Password: {new_password}")
            count += 1
    
    return count

def populate_admin_passwords():
    """Populate temp_passwords for admins"""
    admins = AdminProfile.objects.filter(user__isnull=False)
    count = 0
    
    for admin in admins:
        if admin.user and not admin.user.temp_password:
            new_password = generate_random_password()
            admin.user.temp_password = new_password
            admin.user.save()
            print(f"Admin: {admin.name or admin.email} -> Password: {new_password}")
            count += 1
    
    return count

def populate_all_users():
    """Populate temp_passwords for all users"""
    users = CustomUser.objects.filter(temp_password__isnull=True)
    count = 0
    
    for user in users:
        new_password = generate_random_password()
        user.temp_password = new_password
        user.save()
        print(f"User: {user.username} ({user.email}) -> Password: {new_password}")
        count += 1
    
    return count

if __name__ == '__main__':
    print("=" * 50)
    print("Starting password population...")
    print("=" * 50)
    
    # Method 1: Populate through related models
    student_count = populate_student_passwords()
    teacher_count = populate_teacher_passwords()
    admin_count = populate_admin_passwords()
    
    # Method 2: Populate all users directly
    user_count = populate_all_users()
    
    print("=" * 50)
    print(f"Summary:")
    print(f"  - Students updated: {student_count}")
    print(f"  - Teachers updated: {teacher_count}")
    print(f"  - Admins updated: {admin_count}")
    print(f"  - Total users updated: {user_count}")
    print("=" * 50)