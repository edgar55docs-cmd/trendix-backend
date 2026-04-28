from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/users/', include('apps.users.urls'))
]

def home(request):
    return HttpResponse("""
    <html>
        <head>
            <title>Trendix</title>
        </head>
        <body style="background:black; color:white; text-align:center; margin-top:100px; font-family:sans-serif;">
            <h1>🔥 Trendix Server Live</h1>
            <p>Everything is working</p>
        </body>
    </html>
    """)

if settings.DEBUG:
    urlpatterns += static(
        path('', home),
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )
