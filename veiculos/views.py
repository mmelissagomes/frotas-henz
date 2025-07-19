from django.shortcuts import render

# Create your views here.
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def pagina_veiculos(request):
    return render(request, 'veiculos/home.html')