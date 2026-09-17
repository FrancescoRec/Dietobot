from django.shortcuts import render
from django.contrib.auth.decorators import login_required


@login_required
def home(request):
    """
    Home view - requires authentication.
    """
    return render(request, 'core/home.html')
