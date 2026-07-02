from django.urls import path
from . import views

urlpatterns = [
    path(
        '',
        views.listar_usuarios,
        name='listar_usuarios'
    ),
    path('actualizar-rol/', views.actualizar_rol_usuario, name='actualizar_rol_usuario'),
    path('admin/cancion/eliminar/', views.eliminar_cancion_admin, name='eliminar_cancion_admin'),
    path('admin/album/eliminar/', views.eliminar_album_admin, name='eliminar_album_admin'),

]