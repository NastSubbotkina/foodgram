from rest_framework.pagination import PageNumberPagination

class CustomPagination(PageNumberPagination):
    page_size = 6  
    page_size_query_param = 'limit'  
    

class RecipePagination(PageNumberPagination):
    page_size = 6  # Количество рецептов по умолчанию
    page_size_query_param = 'recipes_limit'  # Параметр для изменения количества рецептов
    