from django.shortcuts import render
from django.db import connection


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