from django.conf import settings
from django.db import transaction
from django.contrib.auth.models import AnonymousUser
from django.core.paginator import Paginator
from rest_framework import serializers

from core.fields import Base64ImageField
from recipes.models import (Ingredient, IngredientRecipe,
                            Recipe, Tag)
from users.models import User


class RecipeSmallReadOnlySerialiazer(serializers.ModelSerializer):

    class Meta:
        model = Recipe
        fields = [
            'id',
            'name',
            'image',
            'cooking_time'
        ]
        read_only_fields = [
            'id',
            'name',
            'image',
            'cooking_time'
        ]


class SubscriptionSerializer(serializers.ModelSerializer):
    recipes = serializers.SerializerMethodField('paginated_recipes')
    recipes_count = serializers.SerializerMethodField()
    is_subscribed = serializers.BooleanField(default=True)

    class Meta:
        model = User
        fields = [
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'recipes',
            'recipes_count',
        ]

    def get_recipes_count(self, obj: User):
        return obj.recipes.count()

    def paginated_recipes(self, obj):
        default_page_size = settings.REST_FRAMEWORK.get('PAGE_SIZE', 6)
        limit = self.context['request'].query_params.get('recipes_limit')
        page_size = limit or default_page_size
        paginator = Paginator(obj.recipes.all(), page_size)
        recipes = paginator.page(1)
        serializer = RecipeSmallReadOnlySerialiazer(recipes, many=True)
        return serializer.data


class TagSerializer(serializers.ModelSerializer):

    class Meta:
        model = Tag
        fields = [
            'id',
            'name',
            'color',
            'slug',
        ]


class IngredientSerializer(serializers.ModelSerializer):

    class Meta:
        model = Ingredient
        fields = [
            'id',
            'name',
            'measure',
        ]


class UserSerializer(serializers.ModelSerializer):

    is_subscribed = serializers.SerializerMethodField(
        read_only=True,
    )

    class Meta:
        model = User
        fields = [
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'password',
            'is_subscribed'
        ]
        read_only_fields = ['id', ]
        extra_kwargs = {
            'password': {'write_only': True},
        }

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user

    def get_is_subscribed(self, obj: User) -> bool:
        user = self.context['request'].user
        if isinstance(user, AnonymousUser):
            return False
        return User.objects.filter(pk=user.pk, subscriptions=obj).exists()


class IngredientRecipeSerializer(serializers.ModelSerializer):

    id = serializers.IntegerField(
        source='ingredient.pk',
        write_only=True,
    )
    name = serializers.CharField(source='ingredient', read_only=True)
    measurement_unit = serializers.CharField(
        source='ingredient.measure', read_only=True
    )

    class Meta:
        model = IngredientRecipe
        fields = [
            'pk',
            'id',
            'name',
            'measurement_unit',
            'amount'
        ]
        extra_kwargs = {
            'amount': {'required': True},
            'id': {'required': True}
        }


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = '__all__'


class RecipeSerializer(serializers.ModelSerializer):
    tags = TagSerializer(
        many=True,
        read_only=True
    )
    author = UserSerializer(
        read_only=True,
        default=serializers.CurrentUserDefault()
    )
    is_favorited = serializers.SerializerMethodField(
        read_only=True,
        required=False
    )
    is_in_shopping_cart = serializers.SerializerMethodField(
        read_only=True,
        required=False
    )
    image = Base64ImageField()
    ingredients = IngredientRecipeSerializer(
        source='ingredientrecipe_set',
        many=True,
        required=True
    )

    class Meta:
        model = Recipe
        fields = [
            'id',
            'tags',
            'author',
            'ingredients',
            'is_favorited',
            'is_in_shopping_cart',
            'name',
            'image',
            'text',
            'cooking_time'
        ]

    def get_is_in_shopping_cart(self, obj):
        if self.context:
            user = self.context['request'].user
            return obj.shopping_users.filter(pk=user.pk).exists()
        return False

    def get_is_favorited(self, obj):
        if self.context:
            user = self.context['request'].user
            return obj.favorited_users.filter(pk=user.pk).exists()
        return False


class RecipeCreateIngredientsSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(write_only=True)

    class Meta:
        model = IngredientRecipe
        fields = ('id', 'amount')


class RecipeCreateSerializer(serializers.ModelSerializer):
    tags = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Tag.objects.all()
    )
    author = UserSerializer(
        read_only=True,
        default=serializers.CurrentUserDefault()
    )
    image = Base64ImageField()
    ingredients = RecipeCreateIngredientsSerializer(
        source='ingredientrecipe_set',
        many=True,
        required=True
    )

    class Meta:
        model = Recipe
        fields = [
            'id',
            'tags',
            'author',
            'ingredients',
            'name',
            'image',
            'text',
            'cooking_time'
        ]

    def validate(self, attrs):
        if len(attrs['tags']) > len(set(attrs['tags'])):
            raise serializers.ValidationError(
                'Unable to add the same tag multiple times.'
            )

        ingredients = [
            item['ingredient'] for item in attrs['recipeingredients']]
        if len(ingredients) > len(set(ingredients)):
            raise serializers.ValidationError(
                'Unable to add the same ingredient multiple times.'
            )

        return attrs

    @transaction.atomic
    def update_or_create_ingredients(self, recipe, ingredients):
        recipe_ingredients = [
            IngredientRecipe(
                recipe=recipe,
                ingredient=current_ingredient['ingredient'],
                amount=current_ingredient['amount'],
            )
            for current_ingredient in ingredients
        ]
        IngredientRecipe.objects.bulk_create(recipe_ingredients)

    @transaction.atomic
    def create(self, validated_data):
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('recipeingredients')
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags)
        self.update_or_create_ingredients(recipe, ingredients)
        return recipe

    @transaction.atomic
    def update(self, instance, validated_data):
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('recipeingredients')
        instance.ingredients.clear()
        instance.tags.clear()
        super().update(instance, validated_data)
        instance.tags.set(tags)
        self.update_or_create_ingredients(instance, ingredients)
        return instance

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        new_tag_representation = []
        tag_ids = ret['tags']
        tags = Tag.objects.filter(pk__in=tag_ids)
        serialized_data = TagSerializer(tags, many=True)
        new_tag_representation = serialized_data.data
        ret['tags'] = new_tag_representation
        return ret


class RecipeSmallSerializer(serializers.ModelSerializer):
    image = Base64ImageField

    class Meta:
        model = Recipe
        fields = [
            'id',
            'name',
            'image',
            'cooking_time'
        ]
