"""
Views para la app 'usuarios' en FluxMusic
Adaptado de MongoDB a SQL Server - Solo funciones necesarias
La conexión (DATABASES) ya está configurada en settings.py, por lo que
aquí simplemente se usa django.db.connection para ejecutar SQL parametrizado.
"""

import hashlib
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import connection, transaction, DatabaseError


def dictfetchone(cursor):
    """Convierte la primera fila del cursor en un diccionario (o None)."""
    columns = [col[0] for col in cursor.description]
    row = cursor.fetchone()
    return dict(zip(columns, row)) if row else None


# ==========================================
# VISTA: MI PERFIL
# ==========================================

def mi_perfil(request):
    """
    Obtiene y muestra el perfil del usuario logueado
    """
    # Verificar que el usuario esté logueado
    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return redirect('login')

    try:
        with connection.cursor() as cursor:
            # No se retorna la contraseña
            cursor.execute("""
                SELECT usuarioId, nickname, email, pais, rolPerfil
                FROM Persona.Usuario
                WHERE usuarioId = %s
            """, [usuario_id])
            usuario = dictfetchone(cursor)

        if not usuario:
            messages.error(request, 'Usuario no encontrado')
            return redirect('login')

        return render(request, 'usuario/perfil.html', {'usuario': usuario})

    except DatabaseError as e:
        messages.error(request, f'Error al obtener perfil: {str(e)}')
        return redirect('/Main/')


# ==========================================
# VISTA: EDITAR PERFIL
# ==========================================

def editar_perfil(request):
    """
    Permite editar el nickname del usuario
    """
    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return redirect('login')

    if request.method == 'POST':
        nuevo_nickname = request.POST.get('nickname', '').strip()

        if not nuevo_nickname:
            messages.error(request, 'El nickname no puede estar vacío')
            return render(request, 'usuario/editar_perfil.html')

        if len(nuevo_nickname) < 3:
            messages.error(request, 'El nickname debe tener al menos 3 caracteres')
            return render(request, 'usuario/editar_perfil.html')

        try:
            with connection.cursor() as cursor:
                # Verificar que el nickname no esté en uso por otro usuario
                cursor.execute("""
                    SELECT usuarioId FROM Persona.Usuario
                    WHERE nickname = %s AND usuarioId <> %s
                """, [nuevo_nickname, usuario_id])

                if cursor.fetchone():
                    messages.error(request, 'Este nickname ya está en uso')
                    return render(request, 'usuario/editar_perfil.html')

                # Actualizar nickname
                cursor.execute("""
                    UPDATE Persona.Usuario
                    SET nickname = %s
                    WHERE usuarioId = %s
                """, [nuevo_nickname, usuario_id])
                modified_count = cursor.rowcount

            if modified_count > 0:
                # Actualizar sesión
                request.session['nickname'] = nuevo_nickname
                messages.success(request, 'Perfil actualizado correctamente')
                return redirect('usuarios:mi_perfil')
            else:
                messages.error(request, 'No se pudo actualizar el perfil')
                return render(request, 'usuario/editar_perfil.html')

        except DatabaseError as e:
            messages.error(request, f'Error al actualizar: {str(e)}')
            return render(request, 'usuario/editar_perfil.html')

    # GET: Mostrar formulario
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT usuarioId, nickname, email, pais, rolPerfil
                FROM Persona.Usuario
                WHERE usuarioId = %s
            """, [usuario_id])
            usuario = dictfetchone(cursor)

        return render(request, 'usuario/editar_perfil.html', {'usuario': usuario})

    except DatabaseError as e:
        messages.error(request, f'Error: {str(e)}')
        return redirect('/Main/')


# ==========================================
# VISTA: CAMBIAR CONTRASEÑA
# ==========================================

def cambiar_password(request):
    """
    Permite cambiar la contraseña del usuario
    """
    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return redirect('login')

    if request.method == 'POST':
        password_actual = request.POST.get('password_actual', '').strip()
        password_nueva = request.POST.get('password_nueva', '').strip()
        password_confirmar = request.POST.get('password_confirmar', '').strip()

        if not password_actual or not password_nueva or not password_confirmar:
            messages.error(request, 'Por favor completa todos los campos')
            return render(request, 'usuario/cambiar_password.html')

        if password_nueva != password_confirmar:
            messages.error(request, 'Las contraseñas nuevas no coinciden')
            return render(request, 'usuario/cambiar_password.html')

        if password_nueva == password_actual:
            messages.error(request, 'La nueva contraseña debe ser diferente a la actual')
            return render(request, 'usuario/cambiar_password.html')

        if len(password_nueva) < 6:
            messages.error(request, 'La contraseña debe tener al menos 6 caracteres')
            return render(request, 'usuario/cambiar_password.html')

        # Mismo esquema de hash (SHA-256, hex en mayúsculas) que usan
        # login_custom y registro_view, y que coincide con
        # CONVERT(VARCHAR(255), HASHBYTES('SHA2_256', @pwd), 2) en SQL Server.
        hash_actual = hashlib.sha256(password_actual.encode('utf-8')).hexdigest().upper()
        hash_nuevo = hashlib.sha256(password_nueva.encode('utf-8')).hexdigest().upper()

        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT [password] FROM Persona.Usuario WHERE usuarioId = %s
                """, [usuario_id])
                usuario = dictfetchone(cursor)

                if not usuario:
                    messages.error(request, 'Usuario no encontrado')
                    return render(request, 'usuario/cambiar_password.html')

                # Verificar que la contraseña actual sea correcta
                if usuario.get('password') != hash_actual:
                    messages.error(request, 'La contraseña actual es incorrecta')
                    return render(request, 'usuario/cambiar_password.html')

                cursor.execute("""
                    UPDATE Persona.Usuario
                    SET [password] = %s
                    WHERE usuarioId = %s
                """, [hash_nuevo, usuario_id])
                modified_count = cursor.rowcount

            if modified_count > 0:
                messages.success(request, 'Contraseña actualizada correctamente')
                return redirect('usuarios:mi_perfil')
            else:
                messages.error(request, 'No se pudo actualizar la contraseña')
                return render(request, 'usuario/cambiar_password.html')

        except DatabaseError as e:
            messages.error(request, f'Error: {str(e)}')
            return render(request, 'usuario/cambiar_password.html')

    # GET: Mostrar formulario
    return render(request, 'usuario/cambiar_password.html')


# ==========================================
# VISTA: ELIMINAR CUENTA
# ==========================================

def eliminar_cuenta(request):
    """
    Elimina la cuenta del usuario y sus dependencias directas
    (equivalente relacional de Persona.sp_eliminar_usuario)
    """
    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return redirect('login')

    if request.method == 'POST':
        try:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    # 1. Dependencias del Oyente (hijos)
                    cursor.execute(
                        "DELETE FROM Streaming.ReproduccionLog WHERE Oyente_usuarioId = %s",
                        [usuario_id]
                    )
                    cursor.execute(
                        "DELETE FROM Streaming.Interaccion WHERE Oyente_usuarioId = %s",
                        [usuario_id]
                    )
                    cursor.execute("""
                        DELETE FROM Streaming.PlaylistCancion
                        WHERE Playlist_playlistID IN (
                            SELECT playlistID FROM Streaming.Playlist WHERE Oyente_usuarioId = %s
                        )
                    """, [usuario_id])
                    cursor.execute(
                        "DELETE FROM Streaming.Playlist WHERE Oyente_usuarioId = %s",
                        [usuario_id]
                    )
                    cursor.execute(
                        "DELETE FROM Ventas.SuscripcionOyente WHERE Oyente_usuarioId = %s",
                        [usuario_id]
                    )

                    # 2. Perfiles específicos
                    cursor.execute("DELETE FROM Persona.Oyente WHERE usuarioId = %s", [usuario_id])
                    cursor.execute("DELETE FROM Persona.Administrador WHERE usuarioId = %s", [usuario_id])
                    cursor.execute("DELETE FROM Persona.Discografica WHERE usuarioId = %s", [usuario_id])
                    cursor.execute("DELETE FROM Persona.Artista WHERE usuarioId = %s", [usuario_id])

                    # 3. Usuario base (padre)
                    cursor.execute("DELETE FROM Persona.Usuario WHERE usuarioId = %s", [usuario_id])
                    deleted_count = cursor.rowcount

            if deleted_count > 0:
                # Limpiar sesión
                request.session.flush()
                messages.success(request, 'Tu cuenta ha sido eliminada correctamente')
                return redirect('login')
            else:
                messages.error(request, 'No se pudo eliminar la cuenta')
                return redirect('usuarios:editar_perfil')

        except DatabaseError as e:
            messages.error(request, f'Error al eliminar: {str(e)}')
            return redirect('usuarios:editar_perfil')

    # GET: Redirigir a editar perfil (donde está el botón)
    return redirect('usuarios:editar_perfil')


# ==========================================
# VISTA: LOGOUT
# ==========================================

def logout_view(request):
    """
    Cierra la sesión del usuario
    """
    request.session.flush()
    messages.success(request, 'Sesión cerrada correctamente')
    return redirect('login')
