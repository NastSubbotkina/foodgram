from rest_framework import permissions

class RecipePermission(permissions.BasePermission):
    """
    Разрешает:
    - Всем пользователям: безопасные методы (GET, HEAD, OPTIONS).
    - Аутентифицированным пользователям: POST.
    - Только автору рецепта: PATCH, DELETE.
    """
    def has_permission(self, request, view):
        # Разрешить всем пользователям безопасные методы
        if request.method in permissions.SAFE_METHODS:
            return True
        # Разрешить аутентифицированным пользователям создавать рецепты
        if request.method == 'POST':
            return request.user.is_authenticated
        # Для PATCH и DELETE проверка выполняется в has_object_permission
        return True

    def has_object_permission(self, request, view, obj):
        # Разрешить PATCH и DELETE только автору рецепта
        if request.method in ['PATCH', 'DELETE']:
            return obj.author == request.user
        return True
