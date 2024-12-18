from django.urls import path
from .views import create_event, event_detail, join_event, manage_participants, event_list, register
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', event_list, name='event_list'),
    path('event/create/', create_event, name='create_event'),
    path('event/<int:event_id>/', event_detail, name='event_detail'),
    path('event/<int:event_id>/join/', join_event, name='join_event'),
    path('event/<int:event_id>/manage/', manage_participants, name='manage_participants'),
    path('accounts/login/', auth_views.LoginView.as_view(template_name='events/login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('register/', register, name='register'),
]
