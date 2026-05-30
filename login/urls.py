from django.urls import path
from . import views

urlpatterns = [
    path(
        'login/',
        views.login_custom,
        name='login'
    ),
    path('registro/', views.registro_view, name='registro'),
]