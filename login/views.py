import hashlib
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import connection, DatabaseError


def dictfetchone(cursor):
    """Convierte la primera fila del cursor en un diccionario (o None)."""
    columns = [col[0] for col in cursor.description]
    row = cursor.fetchone()
    return dict(zip(columns, row)) if row else None


def login_custom(request):
    if request.method == 'POST':
        # Limpieza de espacios y forzar minúsculas en email
        email_input = request.POST.get('email', '').strip().lower()
        password_input = request.POST.get('password', '')

        # Encriptamos la contraseña entrante para que coincida con la BD
        # (mismo formato que CONVERT(VARCHAR(255), HASHBYTES('SHA2_256', ...), 2) en SQL Server)
        hashed_password = hashlib.sha256(password_input.encode('utf-8')).hexdigest().upper()

        try:
            with connection.cursor() as cursor:
                # Buscamos que coincida el email Y la contraseña ya hasheada
                cursor.execute("""
                    SELECT usuarioId, nickname, rolPerfil
                    FROM Persona.Usuario
                    WHERE email = %s AND [password] = %s
                """, [email_input, hashed_password])
                usuario_valido = dictfetchone(cursor)

            if usuario_valido:
                # Limpiamos cualquier dato de sesión de un login anterior
                # (evita que queden mezclados nickname/rol/plan de otra cuenta)
                request.session.flush()

                request.session['usuario_id'] = usuario_valido.get('usuarioId')
                request.session['nickname'] = usuario_valido.get('nickname', 'Usuario')
                request.session['rol'] = usuario_valido.get('rolPerfil', 'Oyente')  # Permisos

                # El plan activo no vive en Usuario; se calcula desde su
                # suscripción vigente (Ventas.SuscripcionOyente + PlanSuscripcion).
                # Si no tiene ninguna suscripción activa, se asume Free por defecto.
                plan_tipo = 'Free'
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT TOP 1 p.tipoPlan
                        FROM Ventas.SuscripcionOyente s
                        INNER JOIN Ventas.PlanSuscripcion p ON s.PlanSuscripcion_planID = p.planID
                        WHERE s.Oyente_usuarioId = %s AND s.estado = 'Activo'
                        ORDER BY s.fechaInicio DESC
                    """, [usuario_valido.get('usuarioId')])
                    plan_row = cursor.fetchone()
                    if plan_row:
                        plan_tipo = plan_row[0]

                request.session['plan_tipo'] = plan_tipo  # Beneficios
                return redirect('/Main/')
            else:
                messages.error(request, "El correo electrónico o la contraseña son incorrectos.")

        except DatabaseError as e:
            messages.error(request, f"Error interno de conexión: {str(e)}")

    return render(request, 'login.html')


def registro_view(request):
    if request.method == 'POST':
        nickname = request.POST.get('nickname', '').strip()
        email = request.POST.get('email', '').strip().lower()
        pais = request.POST.get('pais', '').strip()
        password = request.POST.get('password', '')
        password_confirm = request.POST.get('password_confirm', '')

        if password != password_confirm:
            messages.error(request, 'Las contraseñas no coinciden. Inténtalo de nuevo.')
            return render(request, 'registrarse.html')

        rol_perfil = 'Oyente'

        # Encriptamos la contraseña del nuevo usuario ANTES de guardarla
        hashed_password = hashlib.sha256(password.encode('utf-8')).hexdigest().upper()

        try:
            with connection.cursor() as cursor:
                # Verificar si el correo ya existe
                cursor.execute("SELECT 1 FROM Persona.Usuario WHERE email = %s", [email])
                if cursor.fetchone():
                    messages.error(request, 'Este correo ya está registrado.')
                    return render(request, 'registrarse.html')

                # usuarioId se genera automáticamente vía IDENTITY(1000,1),
                # no es necesario calcularlo manualmente como en Mongo.
                cursor.execute("""
                    INSERT INTO Persona.Usuario (rolPerfil, nickname, email, pais, [password])
                    VALUES (%s, %s, %s, %s, %s)
                """, [rol_perfil, nickname, email, pais, hashed_password])

            messages.success(request, '¡Cuenta creada con éxito! Ya puedes iniciar sesión.')
            return redirect('login')

        except DatabaseError as e:
            messages.error(request, f'Ocurrió un error al crear la cuenta: {str(e)}')
            return render(request, 'registrarse.html')

    return render(request, 'registrarse.html')


def logout_view(request):
    request.session.flush()
    return redirect('login')
