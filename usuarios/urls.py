

from django.urls import path
from . import views

app_name = 'usuarios'

urlpatterns = [
    path('perfil/', views.mi_perfil, name='mi_perfil'),
    path('editar/', views.editar_perfil, name='editar_perfil'),
    path('cambiar-password/', views.cambiar_password, name='cambiar_password'),
    path('eliminar-cuenta/', views.eliminar_cuenta, name='eliminar_cuenta'),
    path('logout/', views.logout_view, name='logout'),

]

