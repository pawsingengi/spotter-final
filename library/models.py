from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.postgres.fields import ArrayField
class User(AbstractUser):
    # Additional fields can be added here if needed
    pass

    class Meta:
        indexes = [
            models.Index(fields=['username']),
            models.Index(fields=['email']),
        ]

class Shelf(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name
class Author(models.Model):
    first_name = models.CharField(max_length=100, db_index=True)
    last_name = models.CharField(max_length=100, db_index=True)
    date_of_birth = models.DateField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['first_name', 'last_name']),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

class Book(models.Model):
    title = models.CharField(max_length=255)
    isbn = models.CharField(max_length=13, blank=True, null=True)
    shelves = models.ManyToManyField(Shelf, related_name='books', blank=True)
    isbn13 = models.CharField(max_length=13, blank=True, null=True)
    language = models.CharField(max_length=50, blank=True, null=True)
    average_rating = models.FloatField(blank=True, null=True)
    book_format = models.CharField(max_length=50, blank=True, null=True)
    num_pages = models.IntegerField(blank=True, null=True)
    publisher = models.CharField(max_length=255, blank=True, null=True)
    publication_date = models.CharField(max_length=50, blank=True, null=True)
    description = models.TextField(blank=True)
    image_url = models.URLField(max_length=500, blank=True, null=True)
    authors = models.ManyToManyField(Author)
    tfidf_vector = models.JSONField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['title']),
            models.Index(fields=['isbn']),
        ]

    def __str__(self):
        return self.title


class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites')
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    added_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'book')
        ordering = ['-added_on']

    def __str__(self):
        return f"{self.user.username} - {self.book.title}"

class BookSimilarity(models.Model):
    book1 = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='similarities_from')
    book2 = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='similarities_to')
    similarity = models.FloatField()

    class Meta:
        unique_together = ('book1', 'book2')
        indexes = [
            models.Index(fields=['book1', 'similarity']),
            models.Index(fields=['book2', 'similarity']),
        ]

    def __str__(self):
        return f"Similarity between {self.book1} and {self.book2}: {self.similarity}"


# class Book(models.Model):
#     title = models.CharField(max_length=255, db_index=True)
#     publication_date = models.DateField(null=True, blank=True)
#     isbn = models.CharField(max_length=13, unique=True, db_index=True)
#     authors = models.ManyToManyField(Author, related_name='books')
#     description = models.TextField(null=True, blank=True)
#     tfidf_vector = models.JSONField(null=True, blank=True)  # Ensure this is JSONField
#
#     class Meta:
#         indexes = [
#             models.Index(fields=['title']),
#             models.Index(fields=['isbn']),
#         ]
#
#     def __str__(self):
#         return self.title

