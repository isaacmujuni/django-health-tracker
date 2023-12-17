from django.shortcuts import render, redirect
from .models import FitnessActivity, DietaryLog
from .forms import UserRegisterForm


def activity_list(request):
    activities = FitnessActivity.objects.filter(user=request.user)
    return render(request, 'fitness/activity_list.html', {'activities': activities})

def diet_log(request):
    diet_logs = DietaryLog.objects.filter(user=request.user)
    return render(request, 'fitness/diet_log.html', {'diet_logs': diet_logs})

def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = UserRegisterForm()
    return render(request, 'fitness/register.html', {'form': form})

def home(request):
    return render(request, 'fitness/home.html')  # Render a template for the home page
