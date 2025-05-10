from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.files.storage import FileSystemStorage
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
import csv
import json
from django.db.models import Count
from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate
from django.contrib import messages
from datetime import datetime, timedelta
from django.utils import timezone

from .models import CustomUser, Record
from .forms import CSVUploadForm, CustomUserCreationForm


def signup(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST, user=request.user)
        if form.is_valid():
            # Extra backend check: only admin can assign admin role
            role = form.cleaned_data['role']
            if role == 'admin' and not (request.user.is_authenticated and request.user.role == 'admin'):
                form.add_error('role', 'Only admins can assign the admin role.')
            else:
                form.save()
                messages.success(request, "Signup completed successfully! You can now log in.")
                return redirect('login')
    else:
        form = CustomUserCreationForm(user=request.user)
    return render(request, 'user/signup.html', {'form': form})


def login_view(request):
    error_message = None
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)

        if user:
            login(request, user)
            if user.is_superuser:  
                return redirect('/admin/')  
            elif user.role == 'admin':  
                return redirect('dashboard')  
            elif user.role == 'employee':
                return redirect('upload')  
        else:
            error_message = "Invalid username or password."

    return render(request, 'user/login.html', {'error': error_message})



# Logout 
def logout_view(request):
    # Handle both GET and POST requests for logout
    if request.user.is_authenticated:
        logout(request)
        messages.success(request, "You have been logged out successfully!")
    return redirect('login')



@login_required
def dashboard(request):
    if request.user.role == 'admin':
        records = Record.objects.all()  
    elif request.user.role == 'employee':
        records = Record.objects.filter(employee=request.user)  
    else:
        records = Record.objects.none()  

    return render(request, 'user/dashboard.html', {'records': records})  



# Upload CSV Records
@login_required
def upload_csv(request):
    if request.method == 'POST':
        form = CSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES['csv_file']
            fs = FileSystemStorage()
            filename = fs.save(csv_file.name, csv_file)

            with open(fs.path(filename), 'r', encoding='utf-8') as file:
                reader = csv.reader(file)
                try:
                    next(reader)  # Skip header row
                    for row in reader:
                        if len(row) < 3:
                            raise ValidationError("CSV format incorrect: Requires 3 columns.")
                        
                        Record.objects.create(
                            employee=request.user,  
                            name=row[0],
                            title=row[1],
                            description=row[2]
                        )

                    messages.success(request, "CSV uploaded successfully!")
                    return redirect('dashboard')
                except Exception as e:
                    messages.error(request, f"Error processing CSV: {e}")
                    return redirect('upload')

    else:
        form = CSVUploadForm()
    return render(request, 'user/upload.html', {'form': form})


# Mark Record as Complete & Schedule Deletion
@login_required
def mark_complete(request, record_id):
    record = get_object_or_404(Record, id=record_id)

   
    if record.employee.email:
        send_mail(
            'Record Completed',
            f'Hello, Your record "{record.description}" has been marked complete.',
            settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'no-reply@example.com',
            [record.employee.email],
        )

   
    if hasattr(record, 'schedule_deletion'):
        record.schedule_deletion()
        messages.success(request, "Record marked as complete and will be deleted after 10 minutes.")
    else:
        messages.error(request, "Error: Record deletion scheduling is not implemented.")

    return redirect('dashboard')


#  Export Records to CSV
@login_required
def export_records(request):
    if request.user.role == 'admin':
        records = Record.objects.all()  
    else:
        records = Record.objects.filter(employee=request.user)  

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="records.csv"'
    writer = csv.writer(response)
    writer.writerow(['Name', 'Title', 'Description'])

    for record in records:
        writer.writerow([record.name, record.title, record.description])

    return response



@login_required
def send_email(request, record_id):
    record = get_object_or_404(Record, id=record_id)

    # Ensure the employee has an email before sending
    if record.employee.email:
        try:
            send_mail(
                subject="Record Information",
                message=f"Here is the record information:\n\nName: {record.name}\nTitle: {record.title}\nDescription: {record.description}",
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[record.employee.email],
                fail_silently=False,
            )
            messages.success(request, "✅ Email sent successfully!")
        except Exception as e:
            messages.error(request, f"❌ Error sending email: {str(e)}")
    else:
        messages.error(request, "❌ Error: Employee does not have an email set.")

    return redirect('dashboard') 


@login_required
def statistics(request):
    """View for displaying record statistics with data visualization"""
    if request.user.role == 'admin':
        # Get all records for admins
        records = Record.objects.all()
    else:
        # Get only user's records for employees
        records = Record.objects.filter(employee=request.user)
    
    # Total records count
    total_records = records.count()
    
    # Records created in the last 7 days
    last_week = timezone.now() - timedelta(days=7)
    recent_records = records.filter(created_at__gte=last_week).count()
    
    # Records by day (last 7 days)
    days = []
    record_counts = []
    
    for i in range(6, -1, -1):
        day = timezone.now() - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        count = records.filter(created_at__range=(day_start, day_end)).count()
        days.append(day.strftime('%a'))
        record_counts.append(count)
    
    # If admin, get records count per employee
    employee_data = []
    if request.user.role == 'admin':
        employee_records = Record.objects.values('employee__username').annotate(
            count=Count('id')
        ).order_by('-count')[:5]  # Top 5 employees
        
        for item in employee_records:
            employee_data.append({
                'name': item['employee__username'],
                'count': item['count']
            })
    
    context = {
        'total_records': total_records,
        'recent_records': recent_records,
        'days': json.dumps(days),
        'record_counts': json.dumps(record_counts),
        'employee_data': json.dumps(employee_data),
    }
    
    return render(request, 'user/statistics.html', context) 