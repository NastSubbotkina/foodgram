from django.contrib import admin
from .models import (
    Ingredient,
    Tag,
    Recipe,
    IngredientInRecipe,
)


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit')
    search_fields = ('name',)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name', 'slug')


class IngredientInRecipeInline(admin.TabularInline):
    model = IngredientInRecipe
    extra = 1
    autocomplete_fields = ['ingredient']


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    inlines = [IngredientInRecipeInline]
    list_display = ('name', 'author__username', 'favorites_count')
    list_filter = ('tags',)
    search_fields = ('name', 'author__username')  # поиск по названию и автору
    
    @admin.display(description='В избранном')
    def favorites_count(self, obj):
        return obj.favorites.count()
  


