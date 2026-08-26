from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("settings", views.settings_view, name="settings"),
    path("session/clear", views.clear_session, name="clear_session"),
    path("session/save", views.save_config, name="save_config"),
    path("course/load", views.load_course, name="load_course"),
    path("course", views.course_tree, name="course_tree"),
    path("course/download", views.download_files, name="download_files"),
]
