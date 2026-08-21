from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("curso/cargar", views.load_course, name="load_course"),
    path("curso/arbol", views.course_tree, name="course_tree"),
    path("curso/descargar", views.download_files, name="download_files"),
]
