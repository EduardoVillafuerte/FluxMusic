from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('login.urls')),
    path('', RedirectView.as_view(url='login/', permanent=False)),
    path('Main/', include('Main.urls')),
    path('usuario_Admin/', include('usuario_Admin.urls')),
    path('usuario/', include('usuarios.urls')),
]
