from django.urls import path
from .views import login_view, logout_view, dashboard, upload_csv, mark_complete, export_records, send_email, signup

urlpatterns = [
    path('', login_view, name='login'),
    path('signup/', signup, name='signup'),
    path('logout/', logout_view, name='logout'),
    path('dashboard/', dashboard, name='dashboard'),
    path('upload/', upload_csv, name='upload'),
    path('complete/<int:record_id>/', mark_complete, name='mark_complete'),
    path('export/', export_records, name='export_records'),  # Added export
    path('send-email/<int:record_id>/', send_email, name='send_email'),  # Added send email
]