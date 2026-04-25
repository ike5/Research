from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),

    # Entries
    path("entries/", views.EntryListView.as_view(), name="entry_list"),
    path("entries/add/", views.entry_add, name="entry_add"),
    path("entries/<int:pk>/", views.EntryDetailView.as_view(), name="entry_detail"),
    path("entries/<int:pk>/edit/", views.entry_edit, name="entry_edit"),
    path("entries/<int:pk>/delete/", views.entry_delete, name="entry_delete"),
    path("entries/<int:pk>/link/", views.entry_link, name="entry_link"),
    path("entries/links/<int:link_pk>/delete/", views.link_delete, name="link_delete"),

    # Reports
    path("reports/", views.ReportListView.as_view(), name="report_list"),
    path("reports/create/", views.report_create, name="report_create"),
    path("reports/<int:pk>/", views.ReportDetailView.as_view(), name="report_detail"),
    path("reports/<int:pk>/delete/", views.report_delete, name="report_delete"),

    # Categories
    path("category/<slug:slug>/", views.category_view, name="category"),

    # Chat
    path("chat/", views.chat_list, name="chat_list"),
    path("chat/new/", views.chat_new, name="chat_new"),
    path("chat/<int:pk>/", views.chat_session, name="chat_session"),
    path("chat/<int:pk>/message/", views.chat_message, name="chat_message"),
    path("chat/<int:pk>/delete/", views.chat_delete, name="chat_delete"),
    path("chat/apply/<int:msg_pk>/<int:entry_pk>/", views.apply_edit_suggestion, name="apply_edit"),

    # Graph
    path("graph/", views.graph_view, name="graph"),
    path("graph/data/", views.graph_data, name="graph_data"),
]
