import hashlib
import base64

from django.db import models
from django.conf import settings


class Ingredient(models.Model):
    name = models.CharField(
        max_length=128,
        verbose_name="Название"
    )
    measurement_unit = models.CharField(
        max_length=64,
        verbose_name="Единица измерения"
    )

    class Meta:
        verbose_name = "Ингредиент"
        verbose_name_plural = "Ингредиенты"

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(
        max_length=32,
        unique=True,
        verbose_name="Название"
    )
    slug = models.SlugField(
        max_length=32,
        unique=True,
        blank=True,
        verbose_name="Слаг"
    )

    class Meta:
        verbose_name = "Тег"
        verbose_name_plural = "Теги"

    def __str__(self):
        return self.name


class Recipe(models.Model):
    name = models.CharField(
        max_length=256,
        verbose_name="Название"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="recipes",
        verbose_name="Автор"
    )
    tags = models.ManyToManyField(
        Tag,
        related_name="recipes",
        verbose_name="Теги"
    )
    ingredients = models.ManyToManyField(
        'Ingredient',
        through='IngredientInRecipe',
        related_name="recipes",
        verbose_name="Ингредиенты"
    )
    image = models.ImageField(
        upload_to='recipes/images/',
        verbose_name="Изображение"
    )
    text = models.TextField(verbose_name="Описание")
    cooking_time = models.PositiveIntegerField(
        verbose_name="Время приготовления (в минутах)"
    )
    pub_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-pub_date']
        verbose_name = "Рецепт"
        verbose_name_plural = "Рецепты"

    def __str__(self):
        return self.name


class IngredientInRecipe(models.Model):
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        related_name="ingredient_in_recipe",
        verbose_name="Ингредиент"
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name="ingredient_in_recipe",
        verbose_name="Рецепт"
    )
    amount = models.PositiveIntegerField(verbose_name="Количество")

    class Meta:
        verbose_name = "Ингредиент в рецепте"
        verbose_name_plural = "Ингредиенты в рецептах"

    def __str__(self):
        return f"{self.ingredient.name} ({self.amount})"


class ShoppingCart(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='shopping_cart'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='in_shopping_cart'
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='unique_shopping_cart'
            )
        ]

    def __str__(self):
        return f"{self.user} -> {self.recipe.name} (ShoppingCart)"


class Favorite(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='favorites'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='favorites'
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='unique_favorite'
            )
        ]

    def __str__(self):
        return f"{self.user} -> {self.recipe.name} (Favorite)"


class ShortLink(models.Model):
    """
    Модель для хранения короткой ссылки на рецепт.
    """
    recipe = models.OneToOneField(
        Recipe,
        on_delete=models.CASCADE,
        related_name='short_link'
    )
    hash = models.CharField(max_length=10, unique=True)

    @staticmethod
    def generate_hash(recipe_id):
        """
        Генерирует хэш для короткой ссылки.
        """
        hash_val = hashlib.sha256(str(recipe_id).encode()).digest()
        # Берём первые 6 байт и кодируем в base64
        return base64.urlsafe_b64encode(hash_val)[:6].decode()

    def save(self, *args, **kwargs):
        """
        Автоматически генерирует хэш при сохранении, если он не установлен.
        """
        if not self.hash:
            self.hash = self.generate_hash(self.recipe_id)
        super().save(*args, **kwargs)