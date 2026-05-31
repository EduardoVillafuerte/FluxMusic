from django.shortcuts import render, redirect
from django.db import connection
from django.contrib import messages


def dashboard_negocio(request):

    # Obtener ID del usuario logueado
    oyente_id = request.session.get(
        'usuario_id'
    )

    # ========= REGALÍAS =========
    reporte_regalias = []

    with connection.cursor() as cursor:

        cursor.execute(
            """
            EXEC Ventas.sp_ProcesarCierreRegalias
            """
        )

        columns = [
            col[0]
            for col in cursor.description
        ]

        reporte_regalias = [
            dict(zip(columns, row))
            for row in cursor.fetchall()
        ]

    # ========= TOP CONSUMO =========
    reporte_consumo = []

    if oyente_id:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                EXEC Streaming.sp_ReporteTopConsumo
                @OyenteId=%s,
                @FechaInicio='2026-04-01',
                @FechaFin='2026-05-23'
                """,
                [oyente_id]
            )

            columns = [
                col[0]
                for col in cursor.description
            ]

            reporte_consumo = [
                dict(zip(columns, row))
                for row in cursor.fetchall()
            ]

    # ========= RECOMENDACIONES =========
    recomendaciones = []

    if oyente_id:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                EXEC Streaming.sp_ReporteRecomendaciones %s
                """,
                [oyente_id]
            )

            columns = [
                col[0]
                for col in cursor.description
            ]

            recomendaciones = [
                dict(zip(columns, row))
                for row in cursor.fetchall()
            ]

    # ========= CONTEXT =========
    context = {

        'nickname': request.session.get(
            'nickname'
        ),

        'role': request.session.get(
            'rol'
        ),

        'reporte_regalias':
            reporte_regalias,

        'reporte_consumo':
            reporte_consumo,

        'recomendaciones':
            recomendaciones
    }

    return render(
        request,
        'main.html',
        context
    )

def dictfetchall(cursor):
    """Retorna todas las filas de un cursor como un diccionario"""
    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]

def mi_biblioteca(request):
    # Validación de seguridad: Comprobar que hay una sesión activa
    if 'usuario_id' not in request.session:
        messages.error(request, "Debes iniciar sesión para ver tu biblioteca.")
        return redirect('login') 

    # Obtener el ID del Oyente desde la sesión
    oyente_id = request.session['usuario_id']

    playlists = []
    albumes = []
    artistas = []

    try:
        with connection.cursor() as cursor:
            # 1. Obtener Playlists creadas por el usuario
            cursor.execute("EXEC Streaming.sp_ReportePlaylistsCreadas @OyenteId = %s", [oyente_id])
            playlists = dictfetchall(cursor)

            # 2. Obtener Álbumes Guardados
            cursor.execute("EXEC Streaming.sp_ReporteAlbumesGuardados @OyenteId = %s", [oyente_id])
            albumes = dictfetchall(cursor)

            # 3. Obtener Artistas Seguidos
            cursor.execute("EXEC Streaming.sp_ReporteArtistasSeguidos @OyenteId = %s", [oyente_id])
            artistas = dictfetchall(cursor)
            
    except Exception as e:
        print(f"Error al cargar la biblioteca desde SQL Server: {e}")
        messages.error(request, "Hubo un error al cargar tu biblioteca. Inténtalo de nuevo más tarde.")

    # Pasar los datos al template
    context = {
        'playlists': playlists,
        'albumes': albumes,
        'artistas': artistas
    }

    return render(request, 'biblioteca.html', context)