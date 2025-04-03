from django.urls import path
from .views import *
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

urlpatterns = [
    path('', landing, name='landing'),  # Page d'accueil
    path('fr/', event_list_fr, name='event_list_fr'),
    path('event/create/', create_event, name='create_event'),
    path('event/<int:event_id>/', event_detail, name='event_detail'),
    path('featured_event/', featured_event, name='featured_event'),
    path('event/<int:event_id>/manage/', manage_participants, name='manage_participants'),
    path('accounts/login/', auth_views.LoginView.as_view(template_name='events/login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('register/', register, name='register'),
    path('profile/<str:username>/', profile, name='profile'),
    path('profile/<str:username>/edit/', edit_profile, name='edit_profile'),
    path('event/<int:event_id>/edit/', edit_event, name='edit_event'),
    path('stripe_webhook/', stripe_webhook, name='stripe_webhook'),
    path('notifications/', notifications, name='notifications_list'),
    path('stripe_success/', stripe_success, name='stripe_success'),
    path('stripe_cancel/', stripe_cancel, name='stripe_cancel'),
    path('about/', TemplateView.as_view(template_name="static/about.html"), name='about'),
    path('cgv/', TemplateView.as_view(template_name="static/cgv.html"), name='cgv'),
    path('cgu/', TemplateView.as_view(template_name="static/cgu.html"), name='cgu'),
    path('mentions-legales/', TemplateView.as_view(template_name="static/legal_mentions.html"), name='mentions_legales'),
    path('confidentialite/', TemplateView.as_view(template_name="static/confidentialite.html"), name='confidentialite'),
    path('certification_demand/', certification_demand, name='certification_demand'),
    path('password_reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
