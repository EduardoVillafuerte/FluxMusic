from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import connection, transaction, DatabaseError


def dictfetchall(cursor):
    """Convierte todas las filas del cursor en una lista de diccionarios."""
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def listar_usuarios(request):
    db = connection  # se mantiene el nombre "db" por familiaridad con la versión anterior

    with db.cursor() as cursor:
        cursor.execute("""
            SELECT usuarioId, rolPerfil, nickname, email, pais
            FROM Persona.Usuario
            ORDER BY usuarioId
        """)
        usuarios = dictfetchall(cursor)

    # ── Canciones del catálogo (con álbum y artista) ──────
    canciones = []
    try:
        with db.cursor() as cursor:
            cursor.execute("""
                SELECT
                    c.cancionId       AS CancionId,
                    c.tituloCancion   AS Cancion,
                    COALESCE(al.tituloAlbum, 'Sin álbum')       AS Album,
                    COALESCE(a.nombreProfesional, 'Desconocido') AS Artista,
                    c.duracionTotal   AS Duracion
                FROM Multimedia.Cancion c
                LEFT JOIN Multimedia.Album al ON c.Album_albumID = al.albumID
                LEFT JOIN Persona.Artista a ON al.Artista_usuarioId = a.usuarioId
                ORDER BY c.tituloCancion ASC
            """)
            canciones = dictfetchall(cursor)
    except DatabaseError as e:
        print(f"Error cargando canciones: {e}")

    # ── Álbumes del catálogo (con artista y total de canciones) ──
    albumes = []
    try:
        with db.cursor() as cursor:
            cursor.execute("""
                SELECT
                    al.albumID        AS AlbumId,
                    al.tituloAlbum    AS Album,
                    COALESCE(a.nombreProfesional, 'Desconocido') AS Artista,
                    al.fechaLanzamiento AS Fecha,
                    (
                        SELECT COUNT(*) FROM Multimedia.Cancion c
                        WHERE c.Album_albumID = al.albumID
                    ) AS TotalCanciones
                FROM Multimedia.Album al
                LEFT JOIN Persona.Artista a ON al.Artista_usuarioId = a.usuarioId
                ORDER BY al.tituloAlbum ASC
            """)
            albumes = dictfetchall(cursor)
    except DatabaseError as e:
        print(f"Error cargando álbumes: {e}")

    # ── Suma total histórica de regalías pagadas ──────────
    # No existe una tabla "liquidaciones" en el modelo relacional; el pago
    # se calcula igual que en Ventas.sp_ProcesarCierreRegalias:
    # cada reproducción válida (aplicarRegalia = 1) paga una tarifa fija de 0.004 USD.
    regalias_totales = 0
    try:
        with db.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) AS TotalStreamsValidos
                FROM Streaming.ReproduccionLog
                WHERE aplicarRegalia = 1
            """)
            total_streams = cursor.fetchone()[0] or 0
            regalias_totales = round(total_streams * 0.004, 2)
    except DatabaseError as e:
        print(f"Error calculando regalías totales: {e}")

    context = {
        'usuarios': usuarios,
        'canciones': canciones,
        'albumes': albumes,
        'regalias_totales': regalias_totales,
    }
    return render(request, 'PanelAdmin.html', context)


def actualizar_rol_usuario(request):
    if request.method == 'POST':
        usuario_id = request.POST.get('usuario_id')
        nuevo_rol = request.POST.get('nuevo_rol')

        if usuario_id and nuevo_rol:
            try:
                with connection.cursor() as cursor:
                    cursor.execute("""
                        UPDATE Persona.Usuario
                        SET rolPerfil = %s
                        WHERE usuarioId = %s
                    """, [nuevo_rol, int(usuario_id)])

            except DatabaseError as e:
                messages.error(request, f"Error en la base de datos: {e}")
        else:
            messages.error(request, "Faltan datos para procesar la solicitud.")

    return redirect('listar_usuarios')


# ============================================================
# Panel Admin — eliminar canción del catálogo
# ============================================================
def eliminar_cancion_admin(request):
    if request.method != 'POST':
        return redirect('listar_usuarios')

    if request.session.get('rol') != 'Administrador':
        messages.error(request, "No autorizado.")
        return redirect('listar_usuarios')

    cancion_id = request.POST.get('cancion_id')
    if not cancion_id:
        messages.error(request, "Falta indicar la canción a eliminar.")
        return redirect('listar_usuarios')

    try:
        cancion_id = int(cancion_id)

        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT tituloCancion FROM Multimedia.Cancion WHERE cancionId = %s
                """, [cancion_id])
                row = cursor.fetchone()

                if not row:
                    messages.error(request, "La canción no existe.")
                    return redirect('listar_usuarios')

                titulo_cancion = row[0]

                # Limpieza de referencias en otras tablas (equivalente a lo que
                # antes se hacía en playlists / interacciones / reproducciones de Mongo)
                cursor.execute(
                    "DELETE FROM Streaming.PlaylistCancion WHERE Cancion_cancionId = %s",
                    [cancion_id]
                )
                cursor.execute(
                    "DELETE FROM Streaming.Interaccion WHERE Cancion_cancionId = %s",
                    [cancion_id]
                )
                cursor.execute(
                    "DELETE FROM Streaming.ReproduccionLog WHERE Cancion_cancionId = %s",
                    [cancion_id]
                )
                cursor.execute(
                    "DELETE FROM Multimedia.CancionGenero WHERE Cancion_cancionId = %s",
                    [cancion_id]
                )

                cursor.execute(
                    "DELETE FROM Multimedia.Cancion WHERE cancionId = %s",
                    [cancion_id]
                )

        messages.success(request, f'"{titulo_cancion or "La canción"}" fue eliminada correctamente.')

    except DatabaseError as e:
        messages.error(request, f"Error al eliminar la canción: {e}")

    return redirect('listar_usuarios')


# ============================================================
# Panel Admin — eliminar álbum (y sus canciones) del catálogo
# ============================================================
def eliminar_album_admin(request):
    if request.method != 'POST':
        return redirect('listar_usuarios')

    if request.session.get('rol') != 'Administrador':
        messages.error(request, "No autorizado.")
        return redirect('listar_usuarios')

    album_id = request.POST.get('album_id')
    if not album_id:
        messages.error(request, "Falta indicar el álbum a eliminar.")
        return redirect('listar_usuarios')

    try:
        album_id = int(album_id)
        canciones_del_album = []

        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT tituloAlbum FROM Multimedia.Album WHERE albumID = %s",
                    [album_id]
                )
                row = cursor.fetchone()

                if not row:
                    messages.error(request, "El álbum no existe.")
                    return redirect('listar_usuarios')

                titulo_album = row[0]

                cursor.execute(
                    "SELECT cancionId FROM Multimedia.Cancion WHERE Album_albumID = %s",
                    [album_id]
                )
                canciones_del_album = [r[0] for r in cursor.fetchall()]

                # Elimina las canciones del álbum y sus referencias
                if canciones_del_album:
                    placeholders = ','.join(['%s'] * len(canciones_del_album))

                    cursor.execute(
                        f"DELETE FROM Streaming.PlaylistCancion WHERE Cancion_cancionId IN ({placeholders})",
                        canciones_del_album
                    )
                    cursor.execute(
                        f"DELETE FROM Streaming.Interaccion WHERE Cancion_cancionId IN ({placeholders})",
                        canciones_del_album
                    )
                    cursor.execute(
                        f"DELETE FROM Streaming.ReproduccionLog WHERE Cancion_cancionId IN ({placeholders})",
                        canciones_del_album
                    )
                    cursor.execute(
                        f"DELETE FROM Multimedia.CancionGenero WHERE Cancion_cancionId IN ({placeholders})",
                        canciones_del_album
                    )

                    cursor.execute(
                        "DELETE FROM Multimedia.Cancion WHERE Album_albumID = %s",
                        [album_id]
                    )

                # Interacciones que apuntan directamente al álbum (ej. "Guardar")
                cursor.execute(
                    "DELETE FROM Streaming.Interaccion WHERE Album_albumID = %s",
                    [album_id]
                )

                cursor.execute(
                    "DELETE FROM Multimedia.Album WHERE albumID = %s",
                    [album_id]
                )

        messages.success(
            request,
            f'El álbum "{titulo_album}" y sus {len(canciones_del_album)} canción(es) fueron eliminados.'
        )

    except DatabaseError as e:
        messages.error(request, f"Error al eliminar el álbum: {e}")

    return redirect('listar_usuarios')
