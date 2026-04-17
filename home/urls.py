from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include("deptts.urls")),
    path('student', include("student.urls")),
    path('teachers', include("teachers.urls")),
    path('subject', include("subject.urls")),
     path('ddcomit', include("ddcomit.urls")),
    path('home_auth', include("home_auth.urls")),  # Note the trailing slash    path('head', include("head.urls")),
    path('fee_system', include("fee_system.urls")),
    path('stu', include("stu.urls")),
    path('Academic', include("Academic.urls")),
    path('exam_mang', include("exam_mang.urls")),
    path('attendance', include("attendance.urls")),
    path('token_app', include("token_app.urls")),
    path('timetables', include("timetables.urls")),
    path('assignm', include("assignm.urls")),





     

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)