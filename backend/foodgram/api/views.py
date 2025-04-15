from django.core.exceptions import PermissionDenied
from django.core.files.storage import default_storage
from django.db.models import F, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from recipes.models import (Favorite, Ingredient, IngredientInRecipe, Recipe,
                            ShoppingCart, ShortLink, Tag)
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


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    permission_classes = [RecipePermission]
    pagination_class = CustomPagination
    filterset_class = RecipeFilter

    def perform_create(self, serializer):
        if self.request.user.is_authenticated:
            serializer.save(author=self.request.user)
        else:
            raise PermissionDenied()

    @action(detail=True, methods=['post', 'delete'])
    def shopping_cart(self, request, pk=None):
        """
        Управляет добавлением и удалением рецепта из корзины покупок.
        """
        recipe = self.get_object()
        user = request.user
        cart_exists = ShoppingCart.objects.filter(
            user=user, recipe=recipe).exists()

        if request.method == 'POST':
            if cart_exists:
                return Response(
                    {"detail": "Рецепт уже добавлен в корзину покупок."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            ShoppingCart.objects.create(user=request.user, recipe=recipe)
            serializer = RecipeShortSerializer(recipe)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if not cart_exists:
            return Response(
                {"errors": "Рецепта нет в корзине."},
                status=status.HTTP_400_BAD_REQUEST
            )
        ShoppingCart.objects.filter(user=user, recipe=recipe).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated]
    )
    def download_shopping_cart(self, request):
        """Формирует и отдает файл со списком покупок."""
        user = request.user
        ingredients_data = IngredientInRecipe.objects.filter(
            recipe__in_shopping_cart__user=user
        ).values(
            name=F('ingredient__name'),
            unit=F('ingredient__measurement_unit')
        ).annotate(
            total_amount=Sum('amount')
        ).order_by('name')

        shopping_list = [
            f"- {item['name']} ({item['unit']}) — {item['total_amount']:.0f}"
            for item in ingredients_data
        ]
        response = HttpResponse(content_type='text/plain')
        response['Content-Disposition'] = 'attachment;' \
            ' filename="shopping_list.txt"'
        response.write("\n".join(shopping_list))
        return response

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticated]
    )
    def favorite(self, request, pk=None):
        """
        Добавляет или удаляет рецепт из избранного.
        """
        user = request.user
        recipe = self.get_object()
        favorite_exists = Favorite.objects.filter(
            user=user, recipe=recipe).exists()

        if request.method == 'POST':
            if favorite_exists:
                return Response(
                    {"errors": "Рецепт уже в избранном."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            Favorite.objects.create(user=user, recipe=recipe)
            serializer = RecipeShortSerializer(recipe)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if not favorite_exists:
            return Response(
                {"errors": "Рецепта нет в избранном."},
                status=status.HTTP_400_BAD_REQUEST
            )
        Favorite.objects.filter(user=user, recipe=recipe).delete()

    @action(detail=True, methods=['get'], url_path='get-link')
    def get_short_link(self, request, pk=None):
        """
        Генерирует или возвращает существующую короткую ссылку для рецепта.
        """
        recipe = self.get_object()
        short_link, _ = ShortLink.objects.get_or_create(recipe=recipe)
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

    def get_serializer_class(self):
        if self.action == 'create':
            return CustomUserCreateSerializer
        if self.action == 'set_password':
            return PasswordChangeSerializer
        if self.action == 'avatar' and self.request.method == 'PUT':
            return CustomUserAvatarSerializer
        if self.action == 'subscriptions':
            return UserWithRecipesSerializer
        return super().get_serializer_class()

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated]
    )
    def me(self, request):
        """Возвращает данные текущего пользователя"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(
        detail=False,
        url_path='me/avatar',
        methods=['put', 'delete'],
        permission_classes=[IsAuthenticated]
    )
    def avatar(self, request):
        """Обновляет или удаляет аватар текущего пользователя."""
        user = request.user
        if request.method == 'PUT':
            serializer = self.get_serializer(user, data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)

        if user.avatar:
            default_storage.delete(user.avatar.name)
            user.avatar = None
            user.save(update_fields=['avatar'])
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=['post'],
        permission_classes=[IsAuthenticated]
    )
    def set_password(self, request):
        """Изменяет пароль текущего пользователя."""
        user = request.user
        serializer = self.get_serializer(
            data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        user.set_password(serializer.validated_data['new_password'])
        user.save()

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated]
    )
    def subscriptions(self, request):
        """
        Получить подписки пользователя.
        """
        user = request.user
        queryset = user.subscriptions.prefetch_related('recipes').all()

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(
                page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(
            queryset, many=True, context={'request': request})
        return Response(serializer.data)

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticated]
    )
    def subscribe(self, request, pk=None):
        """
        Подписывает или отписывает пользователя.
        """
        user_to_subscribe = get_object_or_404(CustomUser, pk=pk)
        user = request.user

        if user == user_to_subscribe:
            return Response(
                {"errors": "Нельзя подписаться на самого себя."},
                status=status.HTTP_400_BAD_REQUEST
            )

        is_subscribed = user.subscriptions.filter(
            id=user_to_subscribe.id).exists()

        if request.method == 'POST':
            if is_subscribed:
                return Response(
                    {"errors": "Вы уже подписаны на этого пользователя."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            user.subscriptions.add(user_to_subscribe)
            serializer = UserWithRecipesSerializer(
                user_to_subscribe, context={'request': request}
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if not is_subscribed:
            return Response(
                {"errors": "Вы не были подписаны на этого пользователя."},
                status=status.HTTP_400_BAD_REQUEST
            )
        user.subscriptions.remove(user_to_subscribe)
        return Response(status=status.HTTP_204_NO_CONTENT)
