from django.shortcuts import render, redirect
from django.contrib import messages
import hashlib #
from .models import PersonaUsuario 
from django.db import connection

def login_custom(request):
    if request.method == 'POST':
        email_input = request.POST.get('email')
        password_input = request.POST.get('password')
        
        # 1. Encriptamos la clave que escribió el usuario (SHA-256 a Hexadecimal en Mayúsculas)
        # Esto genera exactamente el mismo código que hace SQL Server con CONVERT(..., 2)
        hashed_password = hashlib.sha256(password_input.encode('utf-8')).hexdigest().upper()
        
        try:
            # 2. Buscamos en la BD comparando el correo y el HASH (no el texto plano)
            usuario_valido = PersonaUsuario.objects.get(email=email_input, password=hashed_password)
            
            # 3. Si coincide, guardamos la sesión
            request.session['usuario_id'] = usuario_valido.usuarioid
            request.session['nickname'] = usuario_valido.nickname
            request.session['rol'] = usuario_valido.rolperfil
            
            # 4. Redirigimos al panel de usuarios
            # Cambia 'lista_usuarios' por 'listar_usuarios'
            return redirect('dashboard_negocio')
            
        except PersonaUsuario.DoesNotExist:
            # Si el usuario no existe o la clave no coincide, mandamos error
            messages.error(request, "El correo electrónico o la contraseña son incorrectos.")
            
    return render(request, 'login.html')

def registro_view(request):
    if request.method == 'POST':
        nickname = request.POST.get('nickname')
        email = request.POST.get('email')
        pais = request.POST.get('pais')  # <-- AHORA LO CAPTURAMOS DEL HTML
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')

        if password != password_confirm:
            messages.error(request, 'Las contraseñas no coinciden. Inténtalo de nuevo.')
            return render(request, 'registrarse.html')

        rol_perfil = 'Oyente' # Mantenemos el rol por defecto
        # pais = 'Ecuador' <-- BORRAMOS ESTA LÍNEA

        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    EXEC Persona.sp_RegistrarUsuarioConClave 
                        @rolPerfil=%s, 
                        @nickname=%s, 
                        @email=%s, 
                        @pais=%s, 
                        @passwordPlain=%s
                    """,
                    [rol_perfil, nickname, email, pais, password] # Mandamos el país que el usuario escribió
                )
            
            messages.success(request, '¡Cuenta creada con éxito! Ya puedes iniciar sesión.')
            return redirect('login') 

        except Exception as e:
            messages.error(request, f'Ocurrió un error al crear la cuenta: {str(e)}')
            return render(request, 'registrarse.html')

    return render(request, 'registrarse.html')