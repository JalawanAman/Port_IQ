from django.urls import path
from . import views

urlpatterns = [
    path('debug/', views.debug_allowed_hosts),
    path('chat/', views.chat, name='test'),
]
