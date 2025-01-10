from .models import Notification

def unread_notifications_count(request):
    # Si l'utilisateur n'est pas authentifié, retourner 0
    if not request.user.is_authenticated:
        return {'unread_notifications_count': 0}
    
    # Compter les notifications non lues
    count = Notification.objects.filter(user=request.user, is_read=False).count()
    return {'unread_notifications_count': count}
