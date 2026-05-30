from django.shortcuts import render
from django.db import connection

def listar_usuarios(request):

    with connection.cursor() as cursor:

        cursor.execute(
            "EXEC Persona.sp_ConsultarUsuarios"
        )

        columnas = [col[0] for col in cursor.description]

        usuarios = [
            dict(zip(columnas, row))
            for row in cursor.fetchall()
        ]

    return render(
        request,
        'PanelAdmin.html',
        {'usuarios': usuarios}  
    )

# def admin_usuarios(request):

#     conexion = obtener_conexion()
#     cursor = conexion.cursor()

#     cursor.execute(
#         "EXEC sp_listar_usuarios"
#     )

#     usuarios = cursor.fetchall()

#     conexion.close()

#     return render(
#         request,
#         'usuario/listar_usuarios.html',
#         {
#             'usuarios': usuarios
#         }
#     )

# from django.shortcuts import get_object_or_404

# def cambiar_rol_usuario(
#     request,
#     id_usuario
# ):

#     if request.method == 'POST':

#         nuevo_rol = request.POST.get(
#             'rol'
#         )

#         conexion = obtener_conexion()
#         cursor = conexion.cursor()

#         cursor.execute(
#             """
#             EXEC sp_actualizar_rol_usuario ?, ?
#             """,
#             (
#                 id_usuario,
#                 nuevo_rol
#             )
#         )

#         conexion.commit()
#         conexion.close()

#         messages.success(
#             request,
#             'Rol actualizado'
#         )

#     return redirect(
#         'admin_usuarios'
#     )