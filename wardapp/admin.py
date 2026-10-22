from django.contrib import admin
from .models import Area, PromptVersion, Interview, Row, CellReview, RunLog

@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)

@admin.register(PromptVersion)
class PromptVersionAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'created_at')
    search_fields = ('name',)

@admin.register(Interview)
class InterviewAdmin(admin.ModelAdmin):
    list_display = ('id', 'speaker_name', 'speaker_phone', 'area', 'status', 'created_at')
    list_filter = ('status', 'area')
    search_fields = ('speaker_name', 'speaker_phone', 'transcript')

@admin.register(Row)
class RowAdmin(admin.ModelAdmin):
    list_display = ('id', 'interview', 'category', 'sub_category', 'speaker_name', 'area', 'order_no')
    list_filter = ('category', 'area')
    search_fields = ('what', 'why', 'where', 'speaker_name', 'source_quote')

@admin.register(CellReview)
class CellReviewAdmin(admin.ModelAdmin):
    list_display = ('id', 'row', 'field_name', 'is_correct', 'reason', 'created_at')
    list_filter = ('is_correct', 'reason')

@admin.register(RunLog)
class RunLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'interview', 'step', 'started_at', 'ended_at')
