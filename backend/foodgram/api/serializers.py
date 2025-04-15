import base64

from django.core.files.base import ContentFile
from django.core.validators import MinValueValidator
from djoser.serializers import UserCreateSerializer, UserSerializer
from recipes.models import (Favorite, Ingredient, IngredientInRecipe, Recipe,
                            ShoppingCart, Tag)
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from users.models import CustomUser


class Base64ImageField(serializers.ImageField):
    """Кастомное поле для работы с изображениями в base64."""

    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name=f'temp.{ext}')

        return super().to_internal_value(data)


class CustomUserCreateSerializer(UserCreateSerializer):
    """Сериализатор для создания пользователя."""
    class Meta(UserCreateSerializer.Meta):
        model = CustomUser
        fields = (
            'email', 'id', 'username',
            'first_name', 'last_name',
            'password'
        )


class CustomUserSerializer(UserSerializer):
    """Сериализатор для отображения/обновления пользователя."""
    avatar = Base64ImageField(required=False, allow_null=True)
    is_subscribed = serializers.SerializerMethodField()

    class Meta(UserSerializer.Meta):
        model = CustomUser
        fields = (
            'email', 'id', 'username',
            'first_name', 'last_name',
            'is_subscribed', 'avatar'
        )
        read_only_fields = ('id', 'is_subscribed')

    def get_is_subscribed(self, obj):
        """Проверяет, подписан ли текущий пользователь на obj."""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return request.user.subscriptions.filter(id=obj.id).exists()
        return False


class CustomUserAvatarSerializer(serializers.ModelSerializer):
    """Сериализатор для обновления аватара пользователя."""
    avatar = Base64ImageField(required=True, allow_empty_file=False)

    class Meta:
        model = CustomUser
        fields = ('avatar',)


class PasswordChangeSerializer(serializers.Serializer):
    """Сериализатор для смены пароля."""
    current_password = serializers.CharField(
        required=True, write_only=True, style={'input_type': 'password'}
    )
    new_password = serializers.CharField(
        required=True, write_only=True, style={'input_type': 'password'}
    )

    def validate_current_password(self, value):
        """Проверяет правильность текущего пароля."""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            raise ValidationError("Пользователь не аутентифицирован.")
        if not request.user.check_password(value):
            raise ValidationError("Текущий пароль введен неверно.")
        return value


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для ингредиентов."""
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class IngredientInRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для ингредиентов в рецепте (для чтения)."""
    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = IngredientInRecipe
        fields = ('id', 'name', 'measurement_unit', 'amount')
        read_only_fields = ('id', 'name', 'measurement_unit')


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор для тегов."""
    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')
        read_only_fields = ('id', 'name', 'slug')


class RecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для создания, чтения и обновления рецептов."""
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True
    )
    ingredients = serializers.ListField(
        child=serializers.DictField(),
        write_only=True,
        required=True,
        allow_empty=False,
    )
    author = CustomUserSerializer(read_only=True)
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    image = Base64ImageField(required=True, allow_null=False)
    cooking_time = serializers.IntegerField(
        validators=[MinValueValidator(
            1, "Время готовки должно быть >= 1 мин.")],
        min_value=1,
    )

    class Meta:
        model = Recipe
        fields = (
            'id', 'name', 'author', 'tags',
            'is_favorited', 'is_in_shopping_cart',
            'image', 'text', 'cooking_time', 'ingredients'
        )
        read_only_fields = ('id', 'author', 'is_favorited',
                            'is_in_shopping_cart')

    def get_is_in_shopping_cart(self, obj):
        user = self.context['request'].user
        return (
            user.is_authenticated
            and ShoppingCart.objects.filter(user=user, recipe=obj).exists()
        )

    def get_is_favorited(self, obj):
        user = self.context['request'].user
        return (
            user.is_authenticated
            and Favorite.objects.filter(user=user, recipe=obj).exists()
        )

    def to_representation(self, instance):
        """Преобразует объект Recipe в представление для JSON ответа."""
        representation = super().to_representation(instance)
        representation['tags'] = TagSerializer(
            instance.tags.all(),
            many=True,
            read_only=True,
            context=self.context
        ).data
        representation['ingredients'] = IngredientInRecipeSerializer(
            instance.ingredient_in_recipe.all(),
            many=True,
            read_only=True,
            context=self.context
        ).data
        return representation

    def validate_tags(self, data):
        """Валидирует поле tags."""
        if not data:
            raise ValidationError("Нужно выбрать хотя бы один тег.")
        return data

    def validate_ingredients(self, data):
        """Валидирует список входных данных для поля 'ingredients'."""
        if not data:
            raise ValidationError("Добавьте хотя бы один ингредиент.")

        ingredients_validated = []
        ingredient_ids = set()

        for item in data:
            try:
                ingredient_id = int(item['id'])
                amount = int(item['amount'])
            except (ValueError, TypeError, KeyError):
                raise serializers.ValidationError(
                    "Некорректный формат ингредиентов."
                )

            if amount < 1:
                raise serializers.ValidationError(
                    f"Количество ингредиента {ingredient_id} должно быть ≥ 1."
                )

            if ingredient_id in ingredient_ids:
                raise serializers.ValidationError(
                    "Ингредиенты не должны повторяться."
                )
            ingredient_ids.add(ingredient_id)

            ingredients_validated.append(
                {'id': ingredient_id, 'amount': amount})

        existing_ids = set(Ingredient.objects.filter(
            id__in=ingredient_ids
        ).values_list('id', flat=True))

        if existing_ids != ingredient_ids:
            raise serializers.ValidationError(
                "Указаны несуществующие ингредиенты."
            )

        return ingredients_validated

    def create(self, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        tags_data = validated_data.pop('tags')

        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags_data)
        self.create_ingredients(recipe, ingredients_data)

        return recipe

    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop('ingredients', None)
        tags_data = validated_data.pop('tags', None)

        instance = super().update(instance, validated_data)

        if tags_data is not None:
            instance.tags.set(tags_data)

        if ingredients_data is not None:
            instance.ingredient_in_recipe.all().delete()
            self.create_ingredients(instance, ingredients_data)

        return instance

    def create_ingredients(self, recipe, ingredients_data):
        ingredients_to_create = [
            IngredientInRecipe(
                recipe=recipe,
                ingredient_id=ingredient['id'],
                amount=ingredient['amount']
            )
            for ingredient in ingredients_data
        ]
        IngredientInRecipe.objects.bulk_create(ingredients_to_create)


class RecipeShortSerializer(serializers.ModelSerializer):
    """Краткий сериализатор рецепта."""
    image = Base64ImageField(read_only=True)

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')
        read_only_fields = fields


class UserWithRecipesSerializer(CustomUserSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(
        source='recipes.count',
        read_only=True
    )

    class Meta(UserSerializer.Meta):
        fields = CustomUserSerializer.Meta.fields + (
            'recipes', 'recipes_count',)

    def get_recipes(self, obj):
        request = self.context.get('request')
        limit = request.query_params.get('recipes_limit')
        queryset = obj.recipes.all()
        if limit and limit.isdigit():
            queryset = queryset[:int(limit)]
        return RecipeShortSerializer(
            queryset,
            many=True,
            context={'request': request}
        ).data


class ShortLinkSerializer(serializers.Serializer):
    """Сериализатор для генерации короткой ссылки."""
    short_link = serializers.SerializerMethodField()

    def get_short_link(self, obj):
        return f"https://nastfoodgram1.zapto.org/s/{obj.hash}"

    def to_representation(self, instance):
        return {
            'short-link': super().to_representation(instance)['short_link']}
