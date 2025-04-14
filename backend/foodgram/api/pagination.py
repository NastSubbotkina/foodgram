from rest_framework.pagination import PageNumberPagination


class CustomPagination(PageNumberPagination):
    """Кастомная пагинация."""
    page_size = 6
    page_size_query_param = 'limit'


class RecipePagination(PageNumberPagination):
    """Кастомная пагинация для рецептов."""
    page_size = 6
    page_size_query_param = 'recipes_limit'
