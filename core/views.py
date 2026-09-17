from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import redirect, render


@login_required
def home(request):
    """Show the home page to a logged-in user."""

    return render(request, 'core/home.html')


def signup(request):
    """Create a user account and log the new user in."""

    if request.user.is_authenticated:
        return redirect('home')

    form = UserCreationForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect('home')

    return render(request, 'registration/signup.html', {'form': form})
