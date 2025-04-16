from rest_framework import permissions


class RecipePermission(permissions.BasePermission):
    """
    Права доступа для рецептов.
    - Безопасные методы (GET, HEAD, OPTIONS): разрешены всем
    - POST: только аутентифицированным пользователям
    - PATCH/DELETE: только автору рецепта
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.method in ['PATCH', 'DELETE']:
            return obj.author == request.user
        return True
