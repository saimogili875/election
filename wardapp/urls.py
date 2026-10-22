from django.urls import path
from . import views

app_name = 'wardapp'

urlpatterns = [
    # Auth
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # 1. Upload (/)
    path('', views.upload_view, name='upload'),

    # 2. Live Run (/run/<id>/)
    path('run/<int:interview_id>/', views.live_run_view, name='live_run'),
    path('run/<int:interview_id>/stream/', views.live_run_stream, name='live_run_stream'),

    # 3. Sheet (/sheet/)
    path('sheet/', views.sheet_view, name='sheet'),
    path('sheet/export/csv/', views.export_sheet_csv, name='export_sheet_csv'),
    path('interview/<int:interview_id>/export/json/', views.export_interview_json, name='export_interview_json'),
    path('interview/<int:interview_id>/delete/', views.delete_interview_view, name='delete_interview'),
    path('interview/delete-all/', views.delete_all_interviews_view, name='delete_all_interviews'),
    path('api/row/<int:row_id>/update/', views.api_row_update, name='api_row_update'),

    # 4. Review (/review/<id>/)
    path('review/<int:interview_id>/', views.review_view, name='review'),
    path('api/review/save/', views.api_cell_review_save, name='api_cell_review_save'),

    # 5. Prompts (/prompts/)
    path('prompts/', views.prompts_view, name='prompts'),

    # 6. Compare runs (/compare/)
    path('compare/', views.compare_runs_view, name='compare_runs'),
]
