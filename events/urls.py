from django.urls import path
from .views import *
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', event_list, name='event_list'),
    path('event/create/', create_event, name='create_event'),
    path('event/<int:event_id>/', event_detail, name='event_detail'),
    path('event/<int:event_id>/manage/', manage_participants, name='manage_participants'),
    path('accounts/login/', auth_views.LoginView.as_view(template_name='events/login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('register/', register, name='register'),
    path('profile/<str:username>/', profile, name='profile'),
    path('profile/<str:username>/edit/', edit_profile, name='edit_profile'),
    path('event/<int:event_id>/edit/', edit_event, name='edit_event'),
    path('stripe_webhook/', stripe_webhook, name='stripe_webhook'),
    path('notifications/', notifications, name='notifications_list'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
