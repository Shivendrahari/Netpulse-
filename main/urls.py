# main/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_view, name='login'),
    path('register/', views.register, name='register'),
    path('admin_dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('cards/', views.admin_cards, name='cards'),
    path('user_cards/', views.user_cards, name='user_cards'),
    path('access/', views.access, name='access'),
    path('notify/', views.notify, name='notify'),
    path('uptime/', views.uptime, name='uptime'),
    path('User_Uptime/', views.User_Uptime, name='User_Uptime'),
    path('user_dashboard/', views.user_dashboard, name='user_dashboard'),
    path('plot-topology/', views.plot_topology_view, name='plot_topology'),
    path('logout/', views.logout_view, name='logout'),
    path('api/manage-user-access/', views.manage_user_access, name='manage_user_access'),
    path('api/network-data/', views.network_data_api, name='network_data_api'),
    path('api/network-data/manage/', views.manage_network_data, name='manage_network_data'),
    path('api/schedule-email/', views.schedule_email),
    path('update_network_data/', views.update_network_data, name='update_network_data'),
    path('api/uptime/<str:range_type>/', views.get_uptime_data, name='get_uptime_data'),
]
