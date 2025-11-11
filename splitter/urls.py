from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('split/', views.split_dataset, name='split_dataset'),
    path('download/', views.download_splits, name='download_splits'),
]
