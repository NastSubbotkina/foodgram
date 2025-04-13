import base64
from django.core.files.base import ContentFile
from django.core.validators import MinValueValidator
from djoser.serializers import UserCreateSerializer, UserSerializer
from rest_framework import serializers
from recipes.models import (
    Recipe, Tag, Ingredient, IngredientInRecipe, Favorite, ShoppingCart
)
from users.models import CustomUser



class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]

            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)

        return super().to_internal_value(data)
    

class TagsField(serializers.Field):
    def to_representation(self, value):
        """Преобразует объекты тегов в формат для вывода."""
        return TagSerializer(value.all(), many=True).data

    def to_internal_value(self, data):
        if not data:
            raise serializers.ValidationError()
        if not isinstance(data, list):
            raise serializers.ValidationError("Ожидается список ID тегов.")
        
        # Проверяем, что все элементы в списке — числа (ID тегов)
        try:
            tag_ids = [int(id) for id in data]
        except (ValueError, TypeError):
            raise serializers.ValidationError("ID тегов должны быть целыми числами.")
        
        # Проверяем, что все теги существуют
        existing_tags = Tag.objects.filter(id__in=tag_ids)
        if len(existing_tags) != len(tag_ids):
            raise serializers.ValidationError("Один или несколько тегов не существуют.")
        
        return tag_ids


class IngredientsField(serializers.Field):
    def to_representation(self, value):
        """Преобразует объекты IngredientInRecipe в список словарей."""
        return [
            {
                "id": ingredient.ingredient.id,
                "name": ingredient.ingredient.name,
                "measurement_unit": ingredient.ingredient.measurement_unit,
                "amount": ingredient.amount
            }
            for ingredient in value.all()
        ]

    def to_internal_value(self, data):
        """Преобразует список словарей в данные для создания IngredientInRecipe."""
        if not data:
            raise serializers.ValidationError()
        for ingredient_data in data:
            if 'amount' not in ingredient_data or int(ingredient_data['amount']) < 1:
                raise serializers.ValidationError(
                    f"Количество ингредиента с id={ingredient_data['id']} должно быть не меньше 1."
                )
        for ingredient_data in data:
            if not Ingredient.objects.filter(id=ingredient_data['id']).exists():
                raise serializers.ValidationError(
                    f"Ингредиент с id={ingredient_data['id']} не существует."
                )
        ingredient_ids = [ingredient_data['id'] for ingredient_data in data]
        if len(ingredient_ids) != len(set(ingredient_ids)):
            raise serializers.ValidationError("Ингредиенты не должны повторяться.")
    
        return data

class CustomUserCreateSerializer(UserCreateSerializer):
    class Meta(UserCreateSerializer.Meta):
        model = CustomUser
        fields = [
            'email', 'id', 'username', 
            'first_name', 'last_name', 
            'password'
        ]


class CustomUserSerializer(UserSerializer):
    avatar = Base64ImageField(required=False, allow_null=True)
    is_subscribed = serializers.SerializerMethodField()

    class Meta(UserSerializer.Meta):
        model = CustomUser
        fields = [
            'email', 'id', 'username', 
            'first_name', 'last_name', 
            'is_subscribed', 'avatar'
        ]

    def get_is_subscribed(self, obj):
        user = self.context['request'].user
        if user.is_authenticated:
            return user.subscriptions.filter(id=obj.id).exists()
        return False
    
class CustomUserAvatarSerializer(serializers.ModelSerializer):
    avatar = Base64ImageField(required=True, allow_empty_file=False)
    
    class Meta:
        model = CustomUser
        fields = ('avatar',)

   
class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True)

    def validate(self, data):
        # Проверяем, что текущий пароль верен
        user = self.context['request'].user
        if not user.check_password(data['current_password']):
            raise serializers.ValidationError({"current_password": "Текущий пароль введен неверно."})
        return data

class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ['id', 'name', 'measurement_unit']


class IngredientInRecipeSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = IngredientInRecipe
        fields = ('id', 'name', 'measurement_unit', 'amount')


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')


class RecipeSerializer(serializers.ModelSerializer):
    tags = TagsField()
    ingredients = IngredientsField(source='ingredient_in_recipe', required=True)
    author = CustomUserSerializer(read_only=True)   
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    image = Base64ImageField(required=True)
    cooking_time = serializers.IntegerField(validators=[MinValueValidator(1)])

    class Meta:
        model = Recipe
        fields = (
            'id', 'name', 'author', 'tags', 'ingredients',
            'is_favorited', 'is_in_shopping_cart',
            'image', 'text', 'cooking_time'
        )

    def get_is_in_shopping_cart(self, obj):
        user = self.context['request'].user
        if user.is_authenticated:
            return ShoppingCart.objects.filter(user=user, recipe=obj).exists()
        return False       

    def get_is_favorited(self, obj):
        user = self.context['request'].user
        if user.is_authenticated:
            return Favorite.objects.filter(user=user, recipe=obj).exists()
        return False 

    def create(self, validated_data):
        if 'ingredient_in_recipe' not in validated_data:
            raise serializers.ValidationError()
        if 'tags' not in validated_data:
            raise serializers.ValidationError()
        ingredients_data = validated_data.pop('ingredient_in_recipe')
        tags_data = validated_data.pop('tags')
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['author'] = request.user
        recipe = Recipe.objects.create(**validated_data)

        # Добавляем теги
        recipe.tags.set(tags_data)

        # Добавляем ингредиенты
        for ingredient_data in ingredients_data:
            IngredientInRecipe.objects.create(
                recipe=recipe,
                ingredient_id=ingredient_data['id'],
                amount=ingredient_data['amount']
            )

        return recipe

    def update(self, instance, validated_data):
        """Обновление рецепта с ингредиентами и тегами"""
        # Извлекаем данные для связанных полей
        if 'ingredient_in_recipe' not in validated_data:
            raise serializers.ValidationError()
        if 'tags' not in validated_data:
            raise serializers.ValidationError()
        ingredients_data = validated_data.pop('ingredient_in_recipe')
        tags_data = validated_data.pop('tags')

        # Обновляем базовые поля
        instance = super().update(instance, validated_data)

        # Обновляем теги
        instance.tags.clear()
        instance.tags.set(tags_data)

        # Обновляем ингредиенты
        instance.ingredients.clear()
        for ingredient_data in ingredients_data:
            IngredientInRecipe.objects.update_or_create(
                recipe=instance,
                ingredient_id=ingredient_data['id'],
                defaults={'amount': ingredient_data['amount']}
            )

        return instance 
    
class RecipeShortSerializer(serializers.ModelSerializer):
    """Сериализатор для краткого отображения рецепта (используется в ShoppingCart и Favorite)."""
    image = Base64ImageField(read_only=True)  # Поле для обработки изображения в base64

    class Meta:
        model = Recipe
        fields = ['id', 'name', 'image', 'cooking_time']

    
class UserWithRecipesSerializer(CustomUserSerializer):
    recipes = serializers.SerializerMethodField()  # Рецепты автора
    recipes_count = serializers.IntegerField(source='recipes.count', read_only=True)

    class Meta(UserSerializer.Meta):
        fields = CustomUserSerializer.Meta.fields + list(('recipes', 'recipes_count',))

    def get_recipes(self, obj):

        request = self.context.get('request')
        recipes_limit = self.context['request'].query_params.get('recipes_limit')
        recipes = obj.recipes.all()
        if recipes_limit:
            recipes = recipes[:int(recipes_limit)]
        return RecipeShortSerializer(recipes, many=True, context={'request': request}).data    


class ShortLinkSerializer(serializers.Serializer):
    short_link = serializers.SerializerMethodField()

    def get_short_link(self, obj):
        return f"https://localhost/s/{obj.hash}"
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        return {
            'short-link': data['short_link']  # Переименовываем при формировании ответа
        }

    



