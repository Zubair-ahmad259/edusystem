# populate_temp_passwords.py
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'home.settings')
django.setup()

from home_auth.models import CustomUser
from django.utils.crypto import get_random_string

def run():
    users = CustomUser.objects.filter(temp_password__isnull=True)
    count = 0
    for user in users:
        random_password = get_random_string(10)
        user.temp_password = random_password
        user.save()
        print(f"Updated: {user.username} -> {random_password}")
        count += 1
    print(f"Total users updated: {count}")

if __name__ == '__main__':
    run()