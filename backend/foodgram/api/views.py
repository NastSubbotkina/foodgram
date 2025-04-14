from collections import defaultdict

from django.core.files.storage import default_storage
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django_filters.rest_framework import DjangoFilterBackend
from recipes.models import (Favorite, Ingredient, IngredientInRecipe, Recipe,
                            ShoppingCart, ShortLink, Tag)
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from users.models import CustomUser

from .filters import IngredientFilter, RecipeFilter
from .pagination import CustomPagination
from .permissions import RecipePermission
from .serializers import (CustomUserAvatarSerializer,
                          CustomUserCreateSerializer, CustomUserSerializer,
                          IngredientSerializer, PasswordChangeSerializer,
                          RecipeSerializer, RecipeShortSerializer,
                          ShortLinkSerializer, TagSerializer,
                          UserWithRecipesSerializer)


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientFilter
    search_fields = ['name']
    


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    permission_classes = [RecipePermission]
    pagination_class = CustomPagination 
    filterset_class = RecipeFilter
    
    def get_permissions(self):
        if self.action in ['shopping_cart', 'manage_favorite']:
            return [permissions.IsAuthenticated()]
        return [RecipePermission()]

    @action(detail=True, methods=['post', 'delete'], url_path='shopping_cart')  # Добавляем 'delete'
    def shopping_cart(self, request, pk=None):
        """
        Управляет добавлением и удалением рецепта из корзины покупок.
        """
        recipe = self.get_object()  # Получаем рецепт по его ID
        user = request.user

        if request.method == 'POST':
            # Проверяем, не добавлен ли рецепт уже в корзину
            if ShoppingCart.objects.filter(user=user, recipe=recipe).exists():
                return Response(
                    {"detail": "Рецепт уже добавлен в корзину покупок."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Создаем запись в корзине
            ShoppingCart.objects.create(user=request.user, recipe=recipe)

        # Сериализуем связанный рецепт
            serializer = RecipeShortSerializer(recipe)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        elif request.method == 'DELETE':
            # Проверяем, есть ли рецепт в корзине
            try:
                cart_item = ShoppingCart.objects.get(user=user, recipe=recipe)
            except ShoppingCart.DoesNotExist:
                return Response(
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Удаляем запись из корзины
            cart_item.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'], url_path='download_shopping_cart')
    def download_shopping_cart(self, request):
        """
        Скачивает список покупок
        """
        user = request.user
        shopping_cart = ShoppingCart.objects.filter(user=user)

        # Собираем и суммируем ингредиенты
        ingredient_dict = defaultdict(float)
        for cart_item in shopping_cart:
            recipe_ingredients = IngredientInRecipe.objects.filter(recipe=cart_item.recipe)
            for recipe_ingredient in recipe_ingredients:
                key = (recipe_ingredient.ingredient.name, recipe_ingredient.ingredient.measurement_unit)
                ingredient_dict[key] += recipe_ingredient.amount
        
        shopping_list = [
            f"{name} ({unit}) — {amount:.0f}"
            for (name, unit), amount in ingredient_dict.items()
        ]
        response = HttpResponse(content_type='text/plain')
        response['Content-Disposition'] = 'attachment; filename="shopping_list.txt"'
        response.write("\n".join(shopping_list))
        return response

    @action(detail=True, methods=['post', 'delete'], url_path='favorite', permission_classes=[permissions.IsAuthenticated])
    def manage_favorite(self, request, pk=None):
        """
        Добавляет или удаляет рецепт из избранного.
        """
        user = request.user
        recipe = self.get_object()

        if request.method == 'POST':
            # Проверяем, не добавлен ли рецепт уже в избранное
            if Favorite.objects.filter(user=user, recipe=recipe).exists():
                return Response(
                    {"detail": "Рецепт уже в избранном."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Добавляем рецепт в избранное
            Favorite.objects.create(user=user, recipe=recipe)
            serializer = RecipeShortSerializer(recipe)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        elif request.method == 'DELETE':
            # Проверяем, существует ли запись в избранном
            favorite = Favorite.objects.filter(user=user, recipe=recipe)
            if not favorite.exists():
                return Response(
                    status=status.HTTP_400_BAD_REQUEST
                )
            # Удаляем запись из избранного
            favorite.delete()
            return Response(
                {"detail": "Рецепт успешно удален из избранного."},
                status=status.HTTP_204_NO_CONTENT
            )
        
    @action(detail=True, methods=['get'], url_path='get-link')
    def get_short_link(self, request, pk=None):
        """
        Возвращает короткую ссылку для рецепта.
        """
        recipe = self.get_object()

        # Создаем или получаем короткую ссылку
        short_link = ShortLink.objects.get_or_create(recipe=recipe)[0]

        # Сериализуем и возвращаем короткую ссылку
        serializer = ShortLinkSerializer(short_link)
        return Response(serializer.data)
    
    
def redirect_short_link(request, hash):
    """
    Перенаправляет по короткой ссылке на полный рецепт.
    """
    short_link = get_object_or_404(ShortLink, hash=hash)
    return redirect(f'/recipes/{short_link.recipe.id}/')    


class CustomUserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    pagination_class = CustomPagination 

    def create(self, request, *args, **kwargs):
        serializer = CustomUserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def me(self, request):
        # Возвращает данные текущего пользователя
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=False, url_path='me/avatar', methods=['put', 'delete'], permission_classes=[IsAuthenticated])
    def avatar(self, request):
        user = request.user
        if request.method == 'PUT':
            # Обновляет аватар текущего пользователя
            serializer = CustomUserAvatarSerializer(user, data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
        elif request.method == 'DELETE':
            # Удаляет аватар текущего пользователя
            if user.avatar:
                # Удаляем файл аватара из хранилища
                default_storage.delete(user.avatar.path)
                # Очищаем поле аватара в базе данных
                user.avatar = None
                user.save()
            return Response(status=status.HTTP_204_NO_CONTENT)    
        
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def set_password(self, request):
        # Изменение пароля пользователя
        user = request.user
        serializer = PasswordChangeSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        # Сохраняем новый пароль
        user.set_password(serializer.validated_data['new_password'])
        user.save()

        return Response(status=status.HTTP_204_NO_CONTENT)    
    

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated], url_path='subscriptions')
    def subscriptions(self, request):
        """
        Получить список пользователей, на которых подписан текущий пользователь.
        """
        user = request.user
        subscriptions = user.subscriptions.all()
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(subscriptions, request)
    
        if page is not None:
            serializer = UserWithRecipesSerializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)
    
    @action(detail=True, methods=['post', 'delete'], permission_classes=[IsAuthenticated], url_path='subscribe')
    def subscribe(self, request, pk=None):
        """
        Подписаться на пользователя (POST) или отписаться (DELETE).
        """
        user = request.user
        author = self.get_object()

        # Проверка, чтобы пользователь не мог подписаться/отписаться от самого себя
        if user == author:
            return Response(
                {"detail": "Нельзя подписаться или отписаться от самого себя."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if request.method == 'POST':
            # Проверяем, подписан ли пользователь уже на автора
            if user.subscriptions.filter(id=author.id).exists():
                return Response(
                    {"detail": "Вы уже подписаны на этого пользователя."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Подписываемся
            user.subscriptions.add(author)

            # Сериализуем данные автора с использованием UserWithRecipesSerializer
            serializer = UserWithRecipesSerializer(author, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        elif request.method == 'DELETE':
            # Проверяем, подписан ли пользователь на автора
            if not user.subscriptions.filter(id=author.id).exists():
                return Response(
                    {"detail": "Вы не подписаны на этого пользователя."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Отписываемся
            user.subscriptions.remove(author)
            return Response(status=status.HTTP_204_NO_CONTENT)