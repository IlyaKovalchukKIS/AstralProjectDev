from django.urls import path
from . import views

app_name = 'user_app'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/update/', views.profile_update_view, name='profile_update'),
    path('logout/', views.logout_view, name='logout'),
    path('subscriptions/', views.subscription_history_view, name='subscription_history'),
    path('subscription/<int:subscription_id>/', views.subscription_detail_view, name='subscription_detail'),
    path('subscription/<int:subscription_id>/extend/', views.subscription_extend_view, name='subscription_extend'),
    path('subscription/plans/', views.subscription_plans_view, name='subscription_plans'),
]