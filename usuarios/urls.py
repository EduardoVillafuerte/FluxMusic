from django.urls import path
from . import views

urlpatterns = [

    # PERFIL USUARIO
    path('perfil/', views.mi_perfil, name='mi_perfil'),
    path('perfil/editar/', views.editar_perfil, name='editar_perfil'),
    path('perfil/password/', views.cambiar_password, name='cambiar_password'),
    path('perfil/eliminar/', views.eliminar_cuenta, name='eliminar_cuenta'),

]