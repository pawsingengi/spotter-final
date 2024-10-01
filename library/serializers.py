from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import Author, Book, Favorite, Shelf
from django.db import transaction

User = get_user_model()

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, required=True, validators=[validate_password]
    )
    password_confirm = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'password',
            'password_confirm',
            'email',
            'first_name',
            'last_name',
        )
        extra_kwargs = {'email': {'required': True}}

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError(
                {"password": "Password fields didn't match."}
            )
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
        )
        return user

class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Author
        fields = ('id', 'first_name', 'last_name', 'date_of_birth')
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
        }

    def validate(self, attrs):
        if not attrs.get('first_name') or not attrs.get('last_name'):
            raise serializers.ValidationError("Author's first and last name are required.")
        return attrs

class ShelfSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shelf
        fields = ['name']

class BookSerializer(serializers.ModelSerializer):
    authors = AuthorSerializer(many=True)
    shelves = ShelfSerializer(many=True, required=False)

    class Meta:
        model = Book
        fields = (
            'id', 'title', 'publication_date', 'isbn', 'authors', 'shelves', 'description'
        )
        extra_kwargs = {
            'title': {'required': True},
            'isbn': {'required': True},
        }

    def validate(self, attrs):
        if not attrs.get('title') or not attrs.get('isbn'):
            raise serializers.ValidationError("Both title and ISBN are required.")
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        authors_data = validated_data.pop('authors')
        shelves_data = validated_data.pop('shelves', [])
        isbn = validated_data.get('isbn')

        if Book.objects.filter(isbn=isbn).exists():
            raise serializers.ValidationError({'isbn': 'A book with this ISBN already exists.'})

        book = Book.objects.create(**validated_data)

        for author_data in authors_data:
            author = self._get_or_create_author(author_data)
            book.authors.add(author)

        for shelf_data in shelves_data:
            shelf, _ = Shelf.objects.get_or_create(name=shelf_data['name'])
            book.shelves.add(shelf)

        return book

    @transaction.atomic
    def update(self, instance, validated_data):
        authors_data = validated_data.pop('authors')
        shelves_data = validated_data.pop('shelves', [])

        instance.title = validated_data.get('title', instance.title)
        instance.publication_date = validated_data.get('publication_date', instance.publication_date)
        isbn = validated_data.get('isbn', instance.isbn)

        if isbn != instance.isbn and Book.objects.filter(isbn=isbn).exclude(pk=instance.pk).exists():
            raise serializers.ValidationError({'isbn': 'A book with this ISBN already exists.'})
        instance.isbn = isbn

        instance.description = validated_data.get('description', instance.description)
        instance.save()

        instance.authors.clear()
        for author_data in authors_data:
            author = self._get_or_create_author(author_data)
            instance.authors.add(author)

        instance.shelves.clear()
        for shelf_data in shelves_data:
            shelf, _ = Shelf.objects.get_or_create(name=shelf_data['name'])
            instance.shelves.add(shelf)

        return instance

    def _get_or_create_author(self, author_data):
        author, _ = Author.objects.get_or_create(
            first_name=author_data['first_name'],
            last_name=author_data['last_name'],
            defaults={'date_of_birth': author_data.get('date_of_birth')}
        )
        return author

class FavoriteSerializer(serializers.ModelSerializer):
    book_id = serializers.IntegerField(write_only=True)
    book = BookSerializer(read_only=True)

    class Meta:
        model = Favorite
        fields = ('id', 'book_id', 'book', 'added_on')
        read_only_fields = ('id', 'book', 'added_on')

    def validate(self, attrs):
        user = self.context['request'].user
        book_id = attrs.get('book_id')

        if Favorite.objects.filter(user=user, book_id=book_id).exists():
            raise serializers.ValidationError('This book is already in your favorites.')

        favorite_count = Favorite.objects.filter(user=user).count()
        if favorite_count >= 20:
            raise serializers.ValidationError('You can have a maximum of 20 favorite books.')

        return attrs

    def create(self, validated_data):
        user = self.context['request'].user
        book_id = validated_data.pop('book_id')
        book = Book.objects.get(id=book_id)
        favorite = Favorite.objects.create(user=user, book=book)
        return favorite

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        # Add extra responses here
        data.update(
            {
                'user': {
                    'id': self.user.id,
                    'username': self.user.username,
                    'email': self.user.email,
                    'first_name': self.user.first_name,
                    'last_name': self.user.last_name,
                }
            }
        )
        return data
