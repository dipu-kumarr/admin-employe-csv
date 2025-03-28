from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.files.storage import FileSystemStorage
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.conf import settings
from django.http import HttpResponse
from django.contrib import messages
import csv
from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate
from django.contrib import messages

from .models import CustomUser, Record
from .forms import CSVUploadForm, CustomUserCreationForm


def signup(request):
    if request.method == 'POST':
        username = request.POST['username']
        role = request.POST['role']
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']

        if password != confirm_password:
            messages.error(request, "Passwords do not match! Please try again.")
            return redirect('signup')

        # Create user account
        user = CustomUser.objects.create_user(username=username, password=password, role=role)
        messages.success(request, "Signup completed successfully! You can now log in.")
        return redirect('login')

    return render(request, 'user/signup.html')


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
    logout(request)
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
