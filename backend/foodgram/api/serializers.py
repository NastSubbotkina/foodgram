import base64

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.validators import MinValueValidator, MaxValueValidator
from djoser.serializers import UserCreateSerializer, UserSerializer
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from recipes.models import (
    Ingredient,
    IngredientInRecipe,
    Recipe,
    Tag,
)
from users.models import CustomUser
from recipes.constants import (MIN_COOKING_TIME, MAX_COOKING_TIME,
                               MIN_INGREDIENT_AMOUNT, MAX_INGREDIENT_AMOUNT)


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
            'email', 'id', 'username', 'first_name', 'last_name', 'password')


class CustomUserSerializer(UserSerializer):
    """Сериализатор для отображения/обновления пользователя."""

    avatar = Base64ImageField(required=False, allow_null=True)
    is_subscribed = serializers.SerializerMethodField()

    class Meta(UserSerializer.Meta):
        model = CustomUser
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'avatar',
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
            raise ValidationError('Пользователь не аутентифицирован.')
        if not request.user.check_password(value):
            raise ValidationError('Текущий пароль введен неверно.')
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
        source='ingredient.measurement_unit')

    class Meta:
        model = IngredientInRecipe
        fields = ('id', 'name', 'measurement_unit', 'amount')
        read_only_fields = ('id', 'name', 'measurement_unit')


class IngredientAmountSerializer(serializers.Serializer):
    """
    Сериализатор для обработки количества ингредиентов
    при создании/обновлении рецепта.
    """

    id = serializers.IntegerField()
    amount = serializers.IntegerField(
        validators=[
            MinValueValidator(
                MIN_INGREDIENT_AMOUNT,
                message=(
                    f'Количество должно быть больше {MIN_INGREDIENT_AMOUNT}.')
            ),
            MaxValueValidator(
                MAX_INGREDIENT_AMOUNT,
                message=(
                    f'Количество не должно превышать {MAX_INGREDIENT_AMOUNT}.')
            )
        ]
    )


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор для тегов."""

    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')
        read_only_fields = ('id', 'name', 'slug')


class RecipeReadSerializer(serializers.ModelSerializer):
    """Сериализатор для чтения рецептов."""

    tags = TagSerializer(many=True, read_only=True)
    author = CustomUserSerializer(read_only=True)
    ingredients = IngredientInRecipeSerializer(
        source='ingredient_in_recipe', many=True, read_only=True
    )
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    image = Base64ImageField(read_only=True)

    class Meta:
        model = Recipe
        fields = (
            'id',
            'tags',
            'author',
            'ingredients',
            'is_favorited',
            'is_in_shopping_cart',
            'name',
            'image',
            'text',
            'cooking_time',
        )

    def get_is_in_shopping_cart(self, obj):
        user = self.context['request'].user
        return (
            user.is_authenticated
            and user.shopping_cart.filter(recipe=obj).exists()
        )

    def get_is_favorited(self, obj):
        user = self.context['request'].user
        return (
            user.is_authenticated
            and user.favorites.filter(recipe=obj).exists()
        )


class RecipeWriteSerializer(serializers.ModelSerializer):
    """Сериализатор для создания и обновления рецептов."""

    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True)
    ingredients = IngredientAmountSerializer(
        many=True, write_only=True, required=True)
    image = Base64ImageField(required=True, allow_null=False)
    cooking_time = serializers.IntegerField(
        validators=[
            MinValueValidator(
                MIN_COOKING_TIME,
                message=(
                    f'Время готовки должно быть от {MIN_COOKING_TIME} минут.'),
            ),
            MaxValueValidator(
                MAX_COOKING_TIME,
                message=(
                    f'Время готовки должно быть до {MAX_COOKING_TIME} минут.'),
            ),
        ],
    )

    class Meta:
        model = Recipe
        fields = (
            'name', 'tags', 'ingredients', 'image', 'text', 'cooking_time')

    def validate_tags(self, data):
        """Валидирует поле tags."""
        if not data:
            raise ValidationError('Нужно выбрать хотя бы один тег.')
        return data

    def validate_ingredients(self, data):
        """Валидирует список входных данных для поля 'ingredients'."""
        if not data:
            raise ValidationError('Добавьте хотя бы один ингредиент.')

        ingredient_ids = set()

        for item in data:
            ingredient_id = int(item['id'])

            if ingredient_id in ingredient_ids:
                raise serializers.ValidationError(
                    'Ингредиенты не должны повторяться.')
            ingredient_ids.add(ingredient_id)

        existing_ids = set(
            Ingredient.objects.filter(id__in=ingredient_ids).values_list(
                'id', flat=True
            )
        )

        if existing_ids != ingredient_ids:
            raise serializers.ValidationError(
                'Указаны несуществующие ингредиенты.')

        return data

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
                amount=ingredient['amount'],
            )
            for ingredient in ingredients_data
        ]
        IngredientInRecipe.objects.bulk_create(ingredients_to_create)

    def to_representation(self, instance):
        return RecipeReadSerializer(instance, context=self.context).data


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
        source='recipes.count', read_only=True)

    class Meta(UserSerializer.Meta):
        fields = CustomUserSerializer.Meta.fields + (
            'recipes',
            'recipes_count',
        )

    def get_recipes(self, obj):
        request = self.context.get('request')
        limit = request.query_params.get('recipes_limit')
        queryset = obj.recipes.all()
        if limit and limit.isdigit():
            queryset = queryset[: int(limit)]
        return RecipeShortSerializer(
            queryset, many=True, context={'request': request}
        ).data


class SubscriptionValidateSerializer(serializers.Serializer):
    """Сериализатор для валидации запроса на подписку/отписку."""

    def validate(self, data):
        request = self.context.get('request')
        user_to_subscribe = self.context.get('user_to_subscribe')
        user = request.user
        if user == user_to_subscribe:
            raise serializers.ValidationError(
                'Нельзя подписаться на самого себя.')

        is_subscribed = user.subscriptions.filter(
            id=user_to_subscribe.id).exists()

        if request.method == 'POST':
            if is_subscribed:
                raise serializers.ValidationError(
                    'Вы уже подписаны на этого пользователя.')

        elif request.method == 'DELETE':
            if not is_subscribed:
                raise serializers.ValidationError(
                    'Вы не были подписаны на этого пользователя.')
        return data


class ShortLinkSerializer(serializers.Serializer):
    """Сериализатор для генерации короткой ссылки."""

    short_link = serializers.SerializerMethodField()

    def get_short_link(self, obj):
        base = settings.BASE_URL
        prefix = settings.SHORTLINK_PREFIX
        return f"{base}{prefix}/{obj.hash}"

    def to_representation(self, instance):
        return {'short-link':
                super().to_representation(instance)['short_link']}
