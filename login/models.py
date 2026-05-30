from django.db import models

class PersonaUsuario(models.Model):
    usuarioid = models.AutoField(db_column='usuarioId', primary_key=True)
    rolperfil = models.CharField(db_column='rolPerfil', max_length=50) 
    nickname = models.CharField(max_length=70)
    email = models.CharField(max_length=100)
    pais = models.CharField(max_length=70)
    password = models.CharField(max_length=255) 

    class Meta:
        managed = False
        db_table = '[Persona].[Usuario]'