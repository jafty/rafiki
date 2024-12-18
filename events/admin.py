from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Event, Participation

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'date', 'location', 'organizer', 'is_location_hidden')
    list_filter = ('date', 'is_location_hidden')
    search_fields = ('title', 'location', 'description')

@admin.register(Participation)
class ParticipationAdmin(admin.ModelAdmin):
    list_display = ('event', 'user', 'status')
    search_fields = ('event__title', 'user__username')
    list_editable = ('status',)
