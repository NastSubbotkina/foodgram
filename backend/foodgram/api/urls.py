from django.urls import include, path, re_path
from rest_framework.routers import SimpleRouter

from .views import (
    IngredientViewSet, 
    TagViewSet,
    RecipeViewSet,
    CustomUserViewSet
)


router = SimpleRouter()
router.register('users', CustomUserViewSet)
router.register('ingredients', IngredientViewSet)
router.register('tags', TagViewSet)
router.register('recipes', RecipeViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('auth/', include('djoser.urls')),
    re_path(r'^auth/', include('djoser.urls.authtoken')),
]



