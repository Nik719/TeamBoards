# URL routing for all /api/ endpoints
from django.urls import path
from .views import HealthView, RegisterView, LoginView, KBQueryView, AdminUsageSummaryView

urlpatterns = [
    path('health/',              HealthView.as_view(),          name='health'),
    path('auth/register/',       RegisterView.as_view(),        name='register'),
    path('auth/login/',          LoginView.as_view(),           name='login'),
    path('kb/query/',            KBQueryView.as_view(),         name='kb-query'),
    path('admin/usage-summary/', AdminUsageSummaryView.as_view(), name='usage-summary'),
]
