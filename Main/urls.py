from django.urls import path
from . import views

urlpatterns = [
    path(
        '',
        views.dashboard_negocio,
        name='dashboard_negocio'
    ),

    path(
        'biblioteca/',
        views.mi_biblioteca,
        name='mi_biblioteca'
    ),

]