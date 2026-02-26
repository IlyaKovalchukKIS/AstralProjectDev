from django.shortcuts import render

def home(request):
    return render(request, 'home.html')

def tarot(request):
    return render(request, 'tarot.html')

def runes(request):
    return render(request, 'runes.html')

def moon_calendar(request):
    return render(request, 'moon_calendar.html')

def human_design(request):
    return render(request, 'human_design.html')

def about(request):
    return render(request, 'about.html')

def contacts(request):
    return render(request, 'contacts.html')