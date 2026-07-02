from django.urls import path
from . import views

app_name = 'Main'

urlpatterns = [
    path('', views.dashboard_negocio, name='dashboard_negocio'),
    path('biblioteca/', views.mi_biblioteca, name='mi_biblioteca'),
    path('reproducir/', views.registrar_reproduccion, name='registrar_reproduccion'),
    path('biblioteca/agregar/', views.agregar_a_biblioteca, name='agregar_a_biblioteca'),
    path('artista/seguir/', views.seguir_artista, name='seguir_artista'),
    path('playlist/crear/', views.crear_playlist, name='crear_playlist'),
    path('buscar/', views.buscar_canciones, name='buscar_canciones'),
    path('playlist/<int:playlist_id>/', views.playlist_detail, name='playlist_detail'),                   
    path('playlist/agregar-cancion/', views.agregar_cancion_a_playlist, name='agregar_cancion_a_playlist'), 
    path('playlist/quitar-cancion/', views.quitar_cancion_de_playlist, name='quitar_cancion_de_playlist'),  
    path('artista/subir-cancion/', views.subir_cancion, name='subir_cancion'),
    path('planes/', views.ver_planes, name='ver_planes'),
    path('planes/cambiar/', views.cambiar_plan, name='cambiar_plan'),
    path('estadisticas/', views.estadisticas_artista, name='estadisticas_artista'),
    path('salir-discografica/', views.salir_discografica, name='salir_discografica'),
    path('discografica/panel/', views.panel_discografica, name='panel_discografica'),
    path('discografica/vincular/', views.vincular_artista, name='vincular_artista'),
    path('dejar-seguir-artista/', views.dejar_seguir_artista, name='dejar_seguir_artista'),
    path('quitar-de-biblioteca/', views.quitar_de_biblioteca, name='quitar_de_biblioteca'),
    path('canciones-de-artista/', views.canciones_de_artista, name='canciones_de_artista'),
    path('eliminar-playlist/', views.eliminar_playlist, name='eliminar_playlist'),
]