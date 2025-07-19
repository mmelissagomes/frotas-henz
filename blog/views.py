# Create your views here.
from django.http import HttpResponse

def home(request):
    return HttpResponse("Olá, Melissa! Seu site está funcionando lindamente 🚀")
from django.contrib.auth.decorators import login_required


@login_required
def home(request):
    return render(request, 'home.html')
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def home(request):
    return render(request, 'home.html')