from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class FitnessActivity(models.Model):
    ACTIVITY_CHOICES = [
        ('RUN', 'Running'),
        ('YOG', 'Yoga'),
        ('CYC', 'Cycling'),
        # Add more activities as needed
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    activity_type = models.CharField(max_length=3, choices=ACTIVITY_CHOICES)
    duration = models.DurationField()  # e.g., 30 minutes
    intensity = models.CharField(max_length=50)  # e.g., moderate, high
    calories_burned = models.IntegerField()
    date_time = models.DateTimeField()
    def __str__(self):
        return f"{self.activity_type} on {self.date_time.strftime('%Y-%m-%d')}"


class UserProfile(models.Model):
    """
    User Profile
        Extend the default User model using a One-to-One link.
        Fields: date of birth, height, weight, fitness level, etc.
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    date_of_birth = models.DateField()
    height = models.IntegerField()
    weight = models.IntegerField()
    fitness_level = models.IntegerField()

    def __str__(self):
        return f"{self.user.username}'s profile"


class DietaryLog(models.Model):
    """
    Dietary Log
        Fields: user (ForeignKey to User), food item, calories, nutrients (carbs, proteins, fats), quantity, date/time of meal.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    food_item = models.CharField(max_length=50)
    calories = models.IntegerField()
    carbs = models.IntegerField()
    proteins = models.IntegerField()
    fats = models.IntegerField()
    quantity = models.IntegerField()
    date_time = models.DateTimeField()

class FitnessGoal(models.Model):
    """
    Fitness Goal
        Fields: user (ForeignKey to User), goal type (e.g., weight loss, hydration), target value, start date, end date, current progress.
    """
    GOAL_CHOICES = [
        ('WGT', 'Weight Loss'),
        ('HYD', 'Hydration'),
        ('MUS', 'Muscle Gain'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    goal_type = models.CharField(max_length=3, choices=GOAL_CHOICES)
    target_value = models.IntegerField()
    start_date = models.DateField()
    end_date = models.DateField()
    current_progress = models.IntegerField()

    def __str__(self):
        return f"{self.goal_type} goal for {self.user.username}"

class WeightEntry(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    weight = models.FloatField()
    date = models.DateField(default=timezone.now)

    def __str__(self):
        return f'{self.user.username} - {self.weight} kg on {self.date}'