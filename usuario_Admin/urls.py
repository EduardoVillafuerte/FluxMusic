from django.urls import path
from . import views

urlpatterns = [
    path(
        '',
        views.listar_usuarios,
        name='listar_usuarios'
    ),

    # path(
    #     'admin/usuarios/',
    #     views.admin_usuarios,
    #     name='admin_usuarios'
    # ),

    # path(
    #     'admin/usuarios/rol/<int:id_usuario>/',
    #     views.cambiar_rol_usuario,
    #     name='cambiar_rol_usuario'
    # ),
]