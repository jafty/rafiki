# accounts/views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .forms import UsernameForm


@login_required
def post_login_redirect(request):
    user = request.user
    if user.username.startswith("temp_"):
        return redirect('complete_social_signup')
    return redirect('featured_event')


@login_required
def complete_social_signup(request):
    user = request.user

    if not user.username.startswith("temp_"):
        return redirect('edit_profile', username=user.username)

    if request.method == 'POST':
        form = UsernameForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            return redirect('edit_profile', username=user.username)
    else:
        form = UsernameForm(instance=user)

    return render(request, 'accounts/complete_signup.html', {'form': form})
