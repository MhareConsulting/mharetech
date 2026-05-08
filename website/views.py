from django.shortcuts import render


def index(request):
    return render(request, 'index.html')


def mytrack(request):
    return render(request, 'mytrack.html')


def myroutes(request):
    return render(request, 'myroutes.html')
