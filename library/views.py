from rest_framework import generics, viewsets, filters, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.views import APIView
from rest_framework.response import Response

from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.db.models import Sum
from .pagination import StandardResultsSetPagination
from .models import Book, Author, Favorite, BookSimilarity, Shelf
from .serializers import (
    RegisterSerializer,
    CustomTokenObtainPairSerializer,
    BookSerializer,
    AuthorSerializer,
    FavoriteSerializer,
)

User = get_user_model()

def get_recommendations(user):
    favorite_books = Favorite.objects.filter(user=user).values_list('book', flat=True)
    favorite_books = list(favorite_books)

    if not favorite_books:
        return []

    # Get similar books
    similar_books = BookSimilarity.objects.filter(
        book1_id__in=favorite_books
    ).exclude(
        book2_id__in=favorite_books
    ).values(
        'book2_id'
    ).annotate(
        total_similarity=Sum('similarity')
    ).order_by('-total_similarity')[:5]

    # Retrieve book instances
    recommended_books_ids = [item['book2_id'] for item in similar_books]
    recommended_books = Book.objects.filter(id__in=recommended_books_ids)

    serializer = BookSerializer(recommended_books, many=True)
    return serializer.data

class RecommendationView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        recommendations = get_recommendations(user)
        return Response(recommendations, status=status.HTTP_200_OK)

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer

class LoginView(TokenObtainPairView):
    permission_classes = [AllowAny]
    serializer_class = CustomTokenObtainPairSerializer

class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['title', 'authors__first_name', 'authors__last_name']
    pagination_class = StandardResultsSetPagination

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = []  # Allow any
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

class AuthorViewSet(viewsets.ModelViewSet):
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer
    pagination_class = StandardResultsSetPagination

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = []  # Allow any
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

class FavoriteViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    lookup_field = 'book_id'

    def get_queryset(self):
        return Favorite.objects.filter(user=self.request.user)

    def list(self, request):
        favorites = self.get_queryset()
        books = [favorite.book for favorite in favorites]
        serializer = BookSerializer(books, many=True)
        return Response(serializer.data)

    def create(self, request):
        serializer = FavoriteSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        favorite = serializer.save()
        recommendations = get_recommendations(request.user)
        return Response({
            'detail': 'Book added to favorites.',
            'recommendations': recommendations
        }, status=status.HTTP_201_CREATED)

    def destroy(self, request, book_id=None):
        favorite = get_object_or_404(Favorite, user=request.user, book_id=book_id)
        favorite.delete()
        return Response({'detail': 'Book removed from favorites.'}, status=status.HTTP_204_NO_CONTENT)
