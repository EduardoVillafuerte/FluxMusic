from urllib import request

from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import connection


def mi_perfil(request):

    usuario_id = request.session.get(
        'usuario_id'
    )

    with connection.cursor() as cursor:

        cursor.execute(
            "EXEC Persona.sp_obtener_usuario %s",
            [usuario_id]
        )

        usuario = cursor.fetchone()


    return render(
        request,
        'usuario/perfil.html',
        {
            'usuario': usuario
        }
    )


def editar_perfil(request):

    usuario_id = request.session.get(
        'usuario_id'
    )

    if request.method == 'POST':

        nickname = request.POST.get(
            'nickname'
        )

        with connection.cursor() as cursor:

            cursor.execute(
                """
                EXEC Persona.sp_actualizar_nickname %s, %s
                """,
                [
                    usuario_id,
                    nickname
                ]
            )

        request.session['nombre'] = nickname
        request.session['nickname'] = nickname

        messages.success(
            request,
            'Perfil actualizado correctamente'
        )

        return redirect(
            'mi_perfil'
        )

    with connection.cursor() as cursor:

        cursor.execute(
            "EXEC Persona.sp_obtener_usuario %s",
            [usuario_id]
        )
        usuario = cursor.fetchone()

    return render(
        request,
        'usuario/editar_perfil.html',
        {
            'usuario': usuario
        }
    )


def cambiar_password(request):

    usuario_id = request.session.get(
        'usuario_id'
    )

    if request.method == 'POST':

        actual = request.POST.get('password_actual')
        nueva = request.POST.get('password_nueva')
        confirmar = request.POST.get('password_confirmar')

        if not actual or not nueva or not confirmar:
            messages.error(request, 'Por favor completa todos los campos.')
            return redirect('cambiar_password')

        if nueva != confirmar:
            messages.error(request, 'Las contraseñas no coinciden')
            return redirect('cambiar_password')


        try:

            with connection.cursor() as cursor:

                cursor.execute(
                    """
                    EXEC Persona.sp_cambiar_password
                    %s, %s, %s
                    """,
                    [
                        usuario_id,
                        actual,
                        nueva
                    ]
                )

            messages.success(
                request,
                'Contraseña actualizada'
            )

            return redirect(
                'mi_perfil'
            )

        except Exception:

            messages.error(
                request,
                'La contraseña actual es incorrecta'
            )

    return render(
        request,
        'usuario/cambiar_password.html'
    )


def eliminar_cuenta(request):

    if request.method == 'POST':

        usuario_id = request.session.get(
            'usuario_id'
        )

        with connection.cursor() as cursor:

            cursor.execute(
                """
                EXEC Persona.sp_eliminar_usuario %s
                """,
                [usuario_id]
            )
        request.session.flush()

        messages.success(
            request,
            'Tu cuenta fue eliminada'
        )

        return redirect(
            'login'
        )

    return redirect(
        'editar_perfil'
    )

def logout_view(request):

    request.session.flush()

    return redirect('login')