from django.urls import path, include

urlpatterns = [
    path('auth/', include('authapp.urls')),
    path('api/', include('brands_data.urls'))
]
