import os
from django.db import models
from django.utils import timezone
from .constants import REVIEW_REASONS

class Area(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name


class PromptVersion(models.Model):
    name = models.CharField(max_length=100)
    text = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.name} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"


def audio_upload_path(instance, filename):
    return f"audio/{timezone.now().strftime('%Y%m%d_%H%M%S')}_{filename}"


class Interview(models.Model):
    STATUS_CHOICES = [
        ('uploaded', 'Uploaded'),
        ('transcribing', 'Transcribing'),
        ('extracting', 'Extracting Rows'),
        ('done', 'Done'),
        ('failed', 'Failed'),
    ]

    area = models.ForeignKey(Area, on_delete=models.SET_NULL, null=True, blank=True, related_name='interviews')
    speaker_name = models.CharField(max_length=255)
    speaker_phone = models.CharField(max_length=50, blank=True, default='')
    audio_file = models.FileField(upload_to=audio_upload_path)
    transcript = models.TextField(blank=True, default='')
    prompt_version = models.ForeignKey(PromptVersion, on_delete=models.SET_NULL, null=True, blank=True, related_name='interviews')
    model_name = models.CharField(max_length=100, default='gemini-2.5-flash')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='uploaded')
    raw_transcript_response = models.TextField(blank=True, default='')
    raw_extract_response = models.TextField(blank=True, default='')
    error = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        area_str = self.area.name if self.area else "Unknown Area"
        return f"Interview #{self.id} - {self.speaker_name} ({area_str})"

    @property
    def duration_seconds(self):
        if self.finished_at and self.created_at:
            return round((self.finished_at - self.created_at).total_seconds(), 1)
        return None


class Row(models.Model):
    interview = models.ForeignKey(Interview, on_delete=models.CASCADE, related_name='rows')
    area = models.ForeignKey(Area, on_delete=models.SET_NULL, null=True, blank=True)
    speaker_name = models.CharField(max_length=255)
    speaker_phone = models.CharField(max_length=50, blank=True, default='')
    category = models.CharField(max_length=255, default='Other')
    sub_category = models.CharField(max_length=255, default='General')
    order_no = models.PositiveIntegerField(default=1)
    source_quote = models.TextField(blank=True, default='')
    source_time = models.CharField(max_length=50, blank=True, default='')

    # 17 cell fields
    where = models.TextField(blank=True, default='')
    what = models.TextField(blank=True, default='')
    why = models.TextField(blank=True, default='')
    to_people = models.TextField(blank=True, default='')
    how = models.TextField(blank=True, default='')
    solution = models.TextField(blank=True, default='')
    solution_impact = models.TextField(blank=True, default='')
    voter_impact = models.TextField(blank=True, default='')
    vote_plus = models.CharField(max_length=50, blank=True, default='')
    vote_minus = models.CharField(max_length=50, blank=True, default='')
    urgency = models.CharField(max_length=50, blank=True, default='')
    scale = models.CharField(max_length=100, blank=True, default='')
    dept_official = models.TextField(blank=True, default='')
    influencer = models.TextField(blank=True, default='')
    law_route = models.TextField(blank=True, default='')
    work_done = models.TextField(blank=True, default='')
    past_complaint = models.TextField(blank=True, default='')

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['interview', 'category', 'sub_category', 'order_no']

    def __str__(self):
        return f"Row #{self.id} (Interview {self.interview_id}): {self.category} - {self.sub_category}"


class CellReview(models.Model):
    row = models.ForeignKey(Row, on_delete=models.CASCADE, related_name='reviews')
    field_name = models.CharField(max_length=100)
    is_correct = models.BooleanField(default=True)
    reason = models.CharField(max_length=50, choices=REVIEW_REASONS, blank=True, default='')
    note = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('row', 'field_name')

    def __str__(self):
        status = "Correct" if self.is_correct else f"Wrong ({self.reason})"
        return f"Review Row {self.row_id}.{self.field_name}: {status}"


class RunLog(models.Model):
    interview = models.ForeignKey(Interview, on_delete=models.CASCADE, related_name='logs')
    step = models.CharField(max_length=100)
    started_at = models.DateTimeField(default=timezone.now)
    ended_at = models.DateTimeField(null=True, blank=True)
    tokens_in = models.IntegerField(null=True, blank=True)
    tokens_out = models.IntegerField(null=True, blank=True)
    message = models.TextField(blank=True, default='')

    def __str__(self):
        return f"RunLog {self.interview_id} - {self.step}"
