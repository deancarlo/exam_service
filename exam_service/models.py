import uuid

from django.contrib.postgres.fields import ArrayField
from django.db import models


def gen_exam_id():
    return f"exm_{uuid.uuid4().hex[:6]}"


def gen_question_id():
    return f"qst_{uuid.uuid4().hex[:6]}"


def gen_choice_id():
    return f"chc_{uuid.uuid4().hex[:6]}"


def gen_attempt_id():
    return f"att_{uuid.uuid4().hex[:6]}"


class Exam(models.Model):
    id = models.TextField(primary_key=True, default=gen_exam_id)
    title = models.TextField()
    description = models.TextField(null=True, blank=True)
    instruction = models.TextField(null=True, blank=True)
    term = models.IntegerField(null=True, blank=True)
    year = models.IntegerField(null=True, blank=True)
    duration = models.IntegerField()
    passing_score = models.IntegerField()
    item = models.IntegerField(null=True, blank=True)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    instructor_id = models.TextField()
    status = models.TextField(default="PENDING")
    block = ArrayField(models.IntegerField(), default=list, blank=True)
    year_level = ArrayField(models.IntegerField(), default=list, blank=True)
    specific_student_id = ArrayField(models.BigIntegerField(), default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "exams"


class Question(models.Model):
    id = models.TextField(primary_key=True, default=gen_question_id)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, db_column="exam_id")
    question_text = models.TextField()
    question_type = models.TextField()
    order_number = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "questions"


class Choice(models.Model):
    id = models.TextField(primary_key=True, default=gen_choice_id)
    question = models.ForeignKey(
        Question, on_delete=models.CASCADE, db_column="question_id"
    )
    choice_text = models.TextField()
    is_correct = models.BooleanField(default=False)

    class Meta:
        db_table = "choices"


class ExamAttempt(models.Model):
    id = models.TextField(primary_key=True, default=gen_attempt_id)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, db_column="exam_id")
    student_id = models.TextField()
    status = models.TextField(default="IN_PROGRESS")
    time_remaining = models.IntegerField()
    answers = models.JSONField(default=list)
    started_at = models.DateTimeField(auto_now_add=True)
    saved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "exam_attempts"
