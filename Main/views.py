import json
import re
from datetime import datetime

from django.shortcuts import render, redirect
from django.db import connection
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect

def dictfetchall(cursor):
    """Retorna todas las filas de un cursor como una lista de diccionarios"""
    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]


# ============================================================================
# DASHBOARD Y BIBLIOTECA
# ============================================================================

def dashboard_negocio(request):
    oyente_id = request.session.get('usuario_id')
    reporte_regalias = []
    
    with connection.cursor() as cursor:
        cursor.execute("EXEC Ventas.sp_ProcesarCierreRegalias")
        reporte_regalias = dictfetchall(cursor)

    reporte_consumo = []
    recomendaciones = []
    historial_reciente = []

    if oyente_id:
        with connection.cursor() as cursor:
            # Consumo
            cursor.execute(
                """
                EXEC Streaming.sp_ReporteTopConsumo
                @OyenteId=%s,
                @FechaInicio='2026-04-01',
                @FechaFin='2026-05-23'
                """,
                [oyente_id]
            )
            reporte_consumo = dictfetchall(cursor)

            # Recomendaciones
            cursor.execute("EXEC Streaming.sp_ReporteRecomendaciones %s", [oyente_id])
            recomendaciones = dictfetchall(cursor)
            
            # Historial
            cursor.execute("EXEC Streaming.sp_HistorialReproduccion @OyenteId=%s", [oyente_id])
            historial_reciente = dictfetchall(cursor)

    # ========= ADN MUSICAL =========
    adn_musical = {
        'actividad_pct': 0,
        'genero_favorito': 'Sin datos',
        'genero_pct': 0,
        'artista_favorito': 'Sin datos',
        'artista_pct': 0,
        'mood': 'Sin datos',
        'mood_pct': 0,
    }
    if oyente_id:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM Streaming.ReproduccionLog WHERE Oyente_usuarioId = %s", [oyente_id])
            total_plays = cursor.fetchone()[0]

        if total_plays > 0:
            adn_musical['actividad_pct'] = min(100, round((total_plays / 20) * 100))

            with connection.cursor() as cursor:
                cursor.execute("EXEC Streaming.sp_ReportePreferenciasGenero @OyenteId=%s", [oyente_id])
                genero_stats = dictfetchall(cursor)

            if genero_stats:
                top_genero = genero_stats[0]
                adn_musical['genero_favorito'] = top_genero['Genero_Musical']
                total_minutos = sum(g['Minutos_Acumulados'] for g in genero_stats) or 1
                adn_musical['genero_pct'] = round((top_genero['Minutos_Acumulados'] / total_minutos) * 100)
                if len(genero_stats) > 1:
                    segundo = genero_stats[1]
                    adn_musical['mood'] = segundo['Genero_Musical']
                    adn_musical['mood_pct'] = round((segundo['Minutos_Acumulados'] / total_minutos) * 100)
                else:
                    adn_musical['mood'] = top_genero['Genero_Musical']
                    adn_musical['mood_pct'] = adn_musical['genero_pct']

            with connection.cursor() as cursor:
                cursor.execute("EXEC Streaming.sp_ReporteRankingArtistas @OyenteId=%s", [oyente_id])
                artista_stats = dictfetchall(cursor)

            if artista_stats:
                top_artista = artista_stats[0]
                adn_musical['artista_favorito'] = top_artista['Artista']
                total_reproducciones = sum(a['Reproducciones'] for a in artista_stats) or 1
                adn_musical['artista_pct'] = round((top_artista['Reproducciones'] / total_reproducciones) * 100)

    context = {
        'nickname': request.session.get('nickname'),
        'role': request.session.get('rol'),
        'reporte_regalias': reporte_regalias,
        'reporte_consumo': reporte_consumo,
        'recomendaciones': recomendaciones,
        'historial_reciente': historial_reciente,
        'adn_musical': adn_musical,
    }
    return render(request, 'Main.html', context)

def mi_biblioteca(request):
    if 'usuario_id' not in request.session:
        messages.error(request, "Debes iniciar sesión para ver tu biblioteca.")
        return redirect('login')

    oyente_id = request.session['usuario_id']
    playlists, albumes, artistas = [], [], []

    try:
        with connection.cursor() as cursor:
            cursor.execute("EXEC Streaming.sp_ReportePlaylistsCreadas @OyenteId = %s", [oyente_id])
            playlists = dictfetchall(cursor)

            cursor.execute("EXEC Streaming.sp_ReporteAlbumesGuardados @OyenteId = %s", [oyente_id])
            albumes = dictfetchall(cursor)

            cursor.execute("EXEC Streaming.sp_ReporteArtistasSeguidos @OyenteId = %s", [oyente_id])
            artistas = dictfetchall(cursor)
    except Exception as e:
        print(f"Error al cargar la biblioteca SQL: {e}")
        messages.error(request, "Hubo un error al cargar tu biblioteca.")

    context = {
        'playlists': playlists,
        'albumes': albumes,
        'artistas': artistas
    }
    return render(request, 'Biblioteca.html', context)


# ============================================================================
# ACCIONES DE INTERACCIÓN (JS FETCH)
# ============================================================================

@csrf_protect
def registrar_reproduccion(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            oyente_id = request.session.get('usuario_id')
            cancion_id = data.get('cancionId')
            
            if oyente_id and cancion_id:
                with connection.cursor() as cursor:
                    cursor.execute("EXEC Streaming.sp_RegistrarReproduccion @OyenteId=%s, @CancionId=%s", [oyente_id, cancion_id])
            return JsonResponse({'ok': True})
        except Exception as e:
            return JsonResponse({'ok': False, 'error': str(e)})
    return JsonResponse({'ok': False})

def buscar_canciones(request):
    query = request.GET.get('q', '')
    if query:
        with connection.cursor() as cursor:
            cursor.execute("EXEC Multimedia.sp_BuscarCanciones @Termino=%s", [query])
            canciones = dictfetchall(cursor)
            
            resultados = []
            for c in canciones:
                resultados.append({
                    'cancionId': c.get('CancionID'),
                    'titulo': c.get('Titulo'),
                    'artista': c.get('Artista'),
                    'duracion': str(c.get('Duracion', '00:00:00')),
                    'artistaId': c.get('ArtistaID')
                })
            return JsonResponse({'resultados': resultados})
    return JsonResponse({'resultados': []})

def agregar_a_biblioteca(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        oyente_id = request.session.get('usuario_id')
        cancion_id = data.get('cancionId') # <-- Corrección: Capturamos cancionId
        if oyente_id and cancion_id:
            with connection.cursor() as cursor:
                cursor.execute("EXEC Streaming.sp_DarLikeCancion @OyenteId=%s, @CancionId=%s", [oyente_id, cancion_id])
            return JsonResponse({'ok': True, 'mensaje': 'Canción guardada'})
    return JsonResponse({'ok': False})

def quitar_de_biblioteca(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        oyente_id = request.session.get('usuario_id')
        cancion_id = data.get('cancionId') # <-- Corrección: Capturamos cancionId
        if oyente_id and cancion_id:
            with connection.cursor() as cursor:
                cursor.execute("EXEC Streaming.sp_QuitarLikeCancion @OyenteId=%s, @CancionId=%s", [oyente_id, cancion_id])
            return JsonResponse({'ok': True})
    return JsonResponse({'ok': False})

def seguir_artista(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        oyente_id = request.session.get('usuario_id')
        artista_id = data.get('artistaId')
        if oyente_id and artista_id:
            with connection.cursor() as cursor:
                cursor.execute("EXEC Streaming.sp_SeguirArtista @OyenteId=%s, @ArtistaId=%s", [oyente_id, artista_id])
            return JsonResponse({'ok': True, 'mensaje': 'Siguiendo al artista'})
    return JsonResponse({'ok': False})

def dejar_seguir_artista(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        oyente_id = request.session.get('usuario_id')
        artista_id = data.get('artistaId')
        if oyente_id and artista_id:
            with connection.cursor() as cursor:
                cursor.execute("EXEC Streaming.sp_DejarDeSeguirArtista @OyenteId=%s, @ArtistaId=%s", [oyente_id, artista_id])
            return JsonResponse({'ok': True})
    return JsonResponse({'ok': False})

def canciones_de_artista(request):
    artista_id = request.GET.get('artistaId')
    if artista_id:
        with connection.cursor() as cursor:
            cursor.execute("EXEC Multimedia.sp_MisCanciones @ArtistaId=%s", [artista_id])
            filas = dictfetchall(cursor)
            canciones = [{
                'cancionId': f.get('cancionId'),
                'titulo': f.get('Cancion'),
                'duracion': str(f.get('Duracion', '')),
                'artista': f.get('Album') # Adaptado a lo que retorna tu SP
            } for f in filas]
            return JsonResponse({'ok': True, 'canciones': canciones})
    return JsonResponse({'ok': False})


# ============================================================================
# PLAYLISTS
# ============================================================================

def crear_playlist(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        nombre = data.get('nombre')
        oyente_id = request.session.get('usuario_id')
        if oyente_id and nombre:
            try:
                with connection.cursor() as cursor:
                    cursor.execute("""
                        DECLARE @NuevaId INT;
                        EXEC Streaming.sp_CrearPlaylist @OyenteId=%s, @NombrePlaylist=%s, @NuevaPlaylistId=@NuevaId OUTPUT;
                        SELECT @NuevaId;
                    """, [oyente_id, nombre])
                return JsonResponse({'ok': True})
            except Exception as e:
                return JsonResponse({'ok': False, 'error': str(e)})
    return JsonResponse({'ok': False})

def eliminar_playlist(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        playlist_id = data.get('playlistId')
        if playlist_id:
            with connection.cursor() as cursor:
                cursor.execute("EXEC Streaming.sp_EliminarPlaylist @PlaylistId=%s", [playlist_id])
            return JsonResponse({'ok': True})
    return JsonResponse({'ok': False})

def playlist_detail(request, playlist_id):
    if 'usuario_id' not in request.session:
        return redirect('login')

    try:
        with connection.cursor() as cursor:
            # Cabecera de Playlist
            cursor.execute("SELECT playlistId, nombrePlaylist FROM Streaming.Playlist WHERE playlistId = %s", [playlist_id])
            row = cursor.fetchone()
            if not row:
                messages.error(request, "Playlist no encontrada.")
                return redirect('Main:mi_biblioteca')
            
            playlist = {'playlistId': row[0], 'nombrePlaylist': row[1]}

            # Canciones dentro de la Playlist
            cursor.execute("EXEC Streaming.sp_ListarCancionesPlaylist @PlaylistId=%s", [playlist_id])
            canciones = dictfetchall(cursor)

            # Catálogo para buscador modal
            cursor.execute("""
                SELECT c.cancionId, c.tituloCancion AS Titulo, a.nombreProfesional AS Artista, c.duracionTotal AS Duracion, al.albumID
                FROM Multimedia.Cancion c
                INNER JOIN Multimedia.Album al ON c.Album_albumID = al.albumID
                INNER JOIN Persona.Artista a ON al.Artista_usuarioId = a.usuarioId
            """)
            canciones_catalogo = dictfetchall(cursor)

        context = {
            'playlist': playlist,
            'canciones': canciones,
            'canciones_catalogo': canciones_catalogo
        }
        return render(request, 'PlaylistDetail.html', context)
    except Exception as e:
        messages.error(request, f"Error al cargar la playlist: {e}")
        return redirect('Main:mi_biblioteca')

def agregar_cancion_a_playlist(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        playlist_id = data.get('playlistId')
        cancion_id = data.get('cancionId')
        if playlist_id and cancion_id:
            with connection.cursor() as cursor:
                cursor.execute("EXEC Streaming.sp_AgregarCancionPlaylist @PlaylistId=%s, @CancionId=%s", [playlist_id, cancion_id])
            return JsonResponse({'ok': True})
    return JsonResponse({'ok': False})

def quitar_cancion_de_playlist(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        playlist_id = data.get('playlistId')
        cancion_id = data.get('cancionId')
        if playlist_id and cancion_id:
            with connection.cursor() as cursor:
                cursor.execute("EXEC Streaming.sp_EliminarCancionPlaylist @PlaylistId=%s, @CancionId=%s", [playlist_id, cancion_id])
            return JsonResponse({'ok': True})
    return JsonResponse({'ok': False})


# ============================================================================
# PANEL DISCOGRÁFICA
# ============================================================================

def panel_discografica(request):
    if 'usuario_id' not in request.session:
        messages.error(request, "Debes iniciar sesión para acceder a este panel.")
        return redirect('login')

    if request.session.get('rol') != 'Discografica':
        messages.error(request, "No tienes permisos para acceder a esta sección.")
        return redirect('Main:dashboard_negocio')

    discografica_id = request.session['usuario_id']
    artistas_libres, artistas_vinculados = [], []

    try:
        with connection.cursor() as cursor:
            cursor.execute("EXEC Persona.sp_ArtistasLibres")
            filas = dictfetchall(cursor)
            artistas_libres = [
                {
                    'usuarioId': f['usuarioId'], 'nickname': f['nickname'], 'email': f['email'], 'pais': f['pais'],
                    'perfilArtista': {'nombreProfesional': f['nombreProfesional']}
                } for f in filas
            ]

            cursor.execute("EXEC Persona.sp_ArtistasVinculados @DiscograficaId=%s", [discografica_id])
            filas = dictfetchall(cursor)
            artistas_vinculados = [
                {
                    'usuarioId': f['usuarioId'], 'nickname': f['nickname'], 'email': f['email'], 'pais': f['pais'],
                    'perfilArtista': {'nombreProfesional': f['nombreProfesional']}
                } for f in filas
            ]
    except Exception as e:
        messages.error(request, "Hubo un error al cargar la información. Inténtalo de nuevo más tarde.")

    context = {
        'artistas_libres': artistas_libres,
        'artistas_vinculados': artistas_vinculados,
    }
    return render(request, 'PanelDiscografica.html', context)

def vincular_artista(request):
    if request.method != 'POST':
        return redirect('Main:panel_discografica')

    if 'usuario_id' not in request.session or request.session.get('rol') != 'Discografica':
        messages.error(request, "No tienes permisos para realizar esta acción.")
        return redirect('login')

    discografica_id = request.session['usuario_id']
    artista_id = request.POST.get('artista_id')

    if not artista_id:
        messages.error(request, "No se especificó ningún artista para vincular.")
        return redirect('Main:panel_discografica')

    try:
        with connection.cursor() as cursor:
            cursor.execute("EXEC Persona.sp_VincularArtista @ArtistaId=%s, @DiscograficaId=%s", [artista_id, discografica_id])
        messages.success(request, "Artista vinculado correctamente a tu discográfica.")
    except Exception as e:
        print(f"Error al vincular artista: {e}")
        messages.error(request, "No se pudo vincular al artista. Inténtalo de nuevo.")

    return redirect('Main:panel_discografica')

def salir_discografica(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Método no permitido.'}, status=405)

    if 'usuario_id' not in request.session:
        return JsonResponse({'ok': False, 'error': 'Debes iniciar sesión.'}, status=401)

    artista_id = request.session['usuario_id']

    try:
        with connection.cursor() as cursor:
            cursor.execute("EXEC Persona.sp_SalirDiscografica @ArtistaId=%s", [artista_id])
        return JsonResponse({'ok': True, 'mensaje': 'Has salido de tu discográfica correctamente.'})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': 'No se pudo completar la acción. Inténtalo de nuevo.'}, status=500)


# ============================================================================
# PLANES DE SUSCRIPCIÓN
# ============================================================================

def ver_planes(request):
    planes = []
    try:
        with connection.cursor() as cursor:
            cursor.execute("EXEC Ventas.sp_ListarPlanes")
            planes = dictfetchall(cursor)
    except Exception as e:
        messages.error(request, "No se pudieron cargar los planes de suscripción.")

    return render(request, 'Planes.html', {'planes': planes})

def cambiar_plan(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Método no permitido.'}, status=405)

    if 'usuario_id' not in request.session:
        return JsonResponse({'ok': False, 'error': 'Debes iniciar sesión.'}, status=401)

    try:
        data = json.loads(request.body)
        tipo_plan = data.get('tipoPlan')
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({'ok': False, 'error': 'Datos inválidos.'}, status=400)

    if tipo_plan not in ('Free', 'Premium'):
        return JsonResponse({'ok': False, 'error': 'Plan no reconocido.'}, status=400)

    oyente_id = request.session['usuario_id']

    try:
        with connection.cursor() as cursor:
            # Buscamos el plan y el precio
            cursor.execute("SELECT planID, precio FROM Ventas.PlanSuscripcion WHERE tipoPlan = %s", [tipo_plan])
            fila = cursor.fetchone()

        if not fila:
            return JsonResponse({'ok': False, 'error': 'El plan seleccionado no existe.'}, status=404)

        plan_id, precio = fila

        with connection.cursor() as cursor:
            # 🔥 SOLUCIÓN AL ERROR FOREIGN KEY 🔥
            # Verificamos si el usuario existe en Persona.Oyente. Si no existe, lo insertamos con datos por defecto.
            cursor.execute("""
                IF NOT EXISTS (SELECT 1 FROM Persona.Oyente WHERE usuarioId = %s)
                BEGIN
                    INSERT INTO Persona.Oyente (usuarioId, preferenciaAudio, fechaNacimiento, aceptaNotificaciones)
                    VALUES (%s, 'Alta', '2000-01-01', 1)
                END
            """, [oyente_id, oyente_id])

            # Ahora sí, procedemos con el SP de Pago sin que SQL Server nos bloquee
            cursor.execute(
                "EXEC Ventas.sp_ProcesarPagoYSuscripcion @OyenteId=%s, @PlanId=%s, @MontoPagado=%s",
                [oyente_id, plan_id, precio]
            )

        # Reflejar el cambio en la sesión para que el layout actualice la corona
        request.session['plan_tipo'] = tipo_plan
        request.session.modified = True

        return JsonResponse({'ok': True})

    except Exception as e:
        print(f"Error al cambiar de plan: {e}")
        return JsonResponse({'ok': False, 'error': 'No se pudo actualizar el plan. Inténtalo de nuevo.'}, status=500)

# ============================================================================
# SUBIR CANCIÓN
# ============================================================================

def subir_cancion(request):
    if 'usuario_id' not in request.session:
        messages.error(request, "Debes iniciar sesión para subir canciones.")
        return redirect('login')

    artista_id = request.session['usuario_id']

    if request.method == 'POST':
        titulo = request.POST.get('titulo', '').strip()
        duracion = request.POST.get('duracion', '').strip()
        genero = request.POST.get('genero', '').strip()
        album_opcion = request.POST.get('album_opcion')
        album_existente = request.POST.get('album_existente')
        nombre_album_nuevo = request.POST.get('nombre_album_nuevo', '').strip()

        if not titulo or not duracion:
            messages.error(request, "El título y la duración son obligatorios.")
            return redirect('Main:subir_cancion')

        match = re.match(r'^(\d{1,2}):([0-5]\d)$', duracion)
        if not match:
            messages.error(request, "El formato de duración debe ser mm:ss (ej: 3:24).")
            return redirect('Main:subir_cancion')

        duracion_sql = f"00:{int(match.group(1)):02d}:{match.group(2)}"

        try:
            with connection.cursor() as cursor:
                if album_opcion == 'nuevo':
                    if not nombre_album_nuevo:
                        messages.error(request, "Debes indicar el nombre del nuevo álbum.")
                        return redirect('Main:subir_cancion')

                    cursor.execute(
                        """
                        DECLARE @NuevoAlbumId INT;
                        EXEC Multimedia.sp_InsertarAlbum
                            @TituloAlbum=%s,
                            @ArtistaId=%s,
                            @NuevoAlbumId=@NuevoAlbumId OUTPUT;
                        SELECT @NuevoAlbumId;
                        """,
                        [nombre_album_nuevo, artista_id]
                    )
                    album_id = cursor.fetchone()[0]
                else:
                    album_id = album_existente
                    if not album_id:
                        messages.error(request, "Selecciona un álbum existente o crea uno nuevo.")
                        return redirect('Main:subir_cancion')

                cursor.execute(
                    """
                    DECLARE @NuevaCancionId INT;
                    EXEC Multimedia.sp_InsertarCancion
                        @TituloCancion=%s,
                        @Duracion=%s,
                        @AlbumId=%s,
                        @Genero=%s,
                        @NuevaCancionId=@NuevaCancionId OUTPUT;
                    SELECT @NuevaCancionId;
                    """,
                    [titulo, duracion_sql, album_id, genero or None]
                )

            messages.success(request, "¡Canción publicada correctamente!")

        except Exception as e:
            print(f"Error al subir la canción: {e}")
            messages.error(request, "Hubo un error al publicar la canción. Inténtalo de nuevo.")

        return redirect('Main:subir_cancion')

    mis_albumes = []
    mis_canciones = []

    try:
        with connection.cursor() as cursor:
            cursor.execute("EXEC Multimedia.sp_MisAlbumes @ArtistaId=%s", [artista_id])
            mis_albumes = dictfetchall(cursor)

            cursor.execute("EXEC Multimedia.sp_MisCanciones @ArtistaId=%s", [artista_id])
            mis_canciones = dictfetchall(cursor)
    except Exception as e:
        messages.error(request, "Hubo un error al cargar tu información.")

    context = {
        'mis_albumes': mis_albumes,
        'mis_canciones': mis_canciones,
    }
    return render(request, 'SubirCancion.html', context)


# ============================================================================
# ESTADÍSTICAS DEL ARTISTA
# ============================================================================

def estadisticas_artista(request):
    if 'usuario_id' not in request.session:
        messages.error(request, "Debes iniciar sesión para ver tus estadísticas.")
        return redirect('login')

    artista_id = request.session['usuario_id']

    total_reproducciones, total_seguidores, total_likes = 0, 0, 0
    regalias_mes_actual = 0
    reproducciones_por_mes = []
    top_canciones = []
    tiene_discografica = False
    discografica_nombre = None

    try:
        with connection.cursor() as cursor:
            # 1. Totales
            cursor.execute("EXEC Persona.sp_EstadisticasResumenArtista @ArtistaId=%s", [artista_id])
            resumen = dictfetchall(cursor)
            if resumen:
                total_reproducciones = resumen[0]['Total_Reproducciones'] or 0
                total_seguidores = resumen[0]['Total_Seguidores'] or 0
                total_likes = resumen[0]['Total_Likes'] or 0

            # 2. Regalías del mes actual
            cursor.execute("EXEC Ventas.sp_RegaliasMesActualArtista @ArtistaId=%s", [artista_id])
            fila = cursor.fetchone()
            regalias_mes_actual = round(fila[0], 2) if fila and fila[0] else 0

            # 3. Reproducciones por mes
            cursor.execute("EXEC Streaming.sp_ReproduccionesPorMesArtista @ArtistaId=%s", [artista_id])
            meses = dictfetchall(cursor)

            max_total = max((m['Total'] for m in meses), default=0)
            reproducciones_por_mes = [
                {
                    'mes': m['Mes'],
                    'total': m['Total'],
                    'porcentaje': round((m['Total'] / max_total) * 100) if max_total else 0,
                }
                for m in meses
            ]

            # 4. Top 5 canciones
            cursor.execute("EXEC Multimedia.sp_TopCancionesArtista @ArtistaId=%s", [artista_id])
            top_canciones = dictfetchall(cursor)

            # 5. Discográfica actual
            cursor.execute("EXEC Persona.sp_DiscograficaDeArtista @ArtistaId=%s", [artista_id])
            fila = cursor.fetchone()
            if fila and fila[0] is not None:
                tiene_discografica = True
                discografica_nombre = fila[1]

    except Exception as e:
        messages.error(request, "Hubo un error al cargar tus estadísticas.")

    context = {
        'total_reproducciones': total_reproducciones,
        'total_seguidores': total_seguidores,
        'total_likes': total_likes,
        'regalias_mes_actual': regalias_mes_actual,
        'reproducciones_por_mes': reproducciones_por_mes,
        'top_canciones': top_canciones,
        'tiene_discografica': tiene_discografica,
        'discografica_nombre': discografica_nombre,
    }

    return render(request, 'Estadisticas.html', context)