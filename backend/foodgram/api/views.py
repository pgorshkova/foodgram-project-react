from django.contrib.auth.hashers import check_password
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from rest_framework.permissions import SAFE_METHODS, IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import (HTTP_400_BAD_REQUEST, HTTP_204_NO_CONTENT,
                                   HTTP_201_CREATED)
from rest_framework.viewsets import ModelViewSet

from recipes.models import (Favorite, Ingredient, Recipe,
                            ShoppingCart, Tag)
from users.models import User
from .filters import RecipeFilter, IngredientFilter
from .permissions import CustomRecipePermissions
from .serializers import (RecipeSerializer, RecipeCreateSerializer,
                          RecipeSmallSerializer, IngredientSerializer,
                          TagSerializer, UserSerializer,
                          SubscriptionSerializer
                          )


class UserViewSet(ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = []

    @action(
        detail=False,
        methods=['get', ],
        permission_classes=[IsAuthenticated]
    )
    def me(self, *args, **kwargs):
        current_user = self.request.user
        data = UserSerializer(
            current_user,
            context={'request': self.request}
        ).data
        return Response(
            data
        )

    @action(
        detail=False,
        methods=['post', ],
        permission_classes=[IsAuthenticated]
    )
    def set_password(self, request, *args, **kwargs):
        if not (request.data.get('new_password')
                and request.data.get('current_password')):
            return Response(
                {'message': 'Incoming data is not valid.'},
                status=HTTP_400_BAD_REQUEST
            )

        current_user = self.request.user
        current_pass = current_user.password

        if not check_password(
            request.data.get('current_password'), current_pass
        ):
            return Response(
                content_type='application/json',
                data={'current_password': 'Wrong password.'},
                status=HTTP_400_BAD_REQUEST
            )

        current_user.set_password(request.data.get('new_password'))
        current_user.save()

        return Response({'message': 'Password successfully changed.'})

    @action(
        methods=['post', 'delete', ],
        detail=True,
        permission_classes=[IsAuthenticated]
    )
    def subscribe(self, *args, **kwargs):
        current_user = self.request.user
        user_id = self.kwargs.get('pk')
        obj = get_object_or_404(User, pk=user_id)
        subscription = obj.subscribers.filter(id=current_user.id).exists()

        if self.request.method == 'POST':
            if current_user != obj:
                if not subscription:
                    obj.subscribers.add(current_user)
                    data = SubscriptionSerializer(
                        obj,
                        context={'request': self.request}
                    ).data
                    return Response(
                        data=data,
                        status=HTTP_201_CREATED
                    )
                else:
                    return Response(
                        data={'error': 'You subscribed to this user.'},
                        status=HTTP_400_BAD_REQUEST
                    )
            return Response(
                data={'error': 'You cannot subscribe to yourself.'},
                status=HTTP_400_BAD_REQUEST
            )

        if current_user != obj:
            if subscription:
                obj.subscribers.remove(current_user)
                return Response(
                    data={'message': 'You unsubscribed from the user.'},
                    status=HTTP_204_NO_CONTENT
                )
            else:
                return Response(
                    data={'error': 'You have not subscribed yet.'},
                    status=HTTP_400_BAD_REQUEST
                )

        return Response(
            status=HTTP_400_BAD_REQUEST
        )

    @action(
        methods=['get', ],
        detail=False,
        permission_classes=[IsAuthenticated]
    )
    def subscriptions(self, *args, **kwargs):
        user_subscriptions = self.request.user.subscriptions.all()
        serializer = SubscriptionSerializer(
            user_subscriptions,
            many=True,
            context={'request': self.request}
        )
        queryset = self.paginate_queryset(serializer.data)
        return self.get_paginated_response(queryset)


class RecipeViewSet(ModelViewSet):
    queryset = Recipe.objects.all()
    permission_classes = [CustomRecipePermissions]
    filter_backends = [DjangoFilterBackend, ]
    filterset_class = RecipeFilter
    http_method_names = ['get', 'post', 'patch', 'delete', ]

    def get_serializer_class(self):
        if self.request.method in SAFE_METHODS:
            return RecipeSerializer
        return RecipeCreateSerializer

    def perform_create(self, serializer):
        serializer.is_valid(raise_exception=True)
        serializer.save(
            author=self.request.user,
        )

    def get_recipe(self):
        return get_object_or_404(Recipe, pk=self.kwargs.get('pk'))

    @action(
        detail=False,
        methods=['get', ],
        permission_classes=[IsAuthenticated]
    )
    def download_shopping_cart(self, *args, **kwargs):
        Recipe._meta.ordering = []
        queryset = (Recipe.objects.filter(
            shopping_users=self.request.user).values(
            'ingredients__measure', 'ingredients__name').annotate(
            all_amount=Sum('ingredientrecipe__amount')
        ))
        response = HttpResponse(content_type='text/plain')
        response['Content-Disposition'] = ('attachment;'
                                           'filename="shopping_list.txt"')
        data = '\n'.join([
            ' '.join(
                [
                    str(ingredient['ingredients__name']),
                    str(ingredient['all_amount']),
                    str(ingredient['ingredients__measure']),
                ]
            )
            for ingredient in queryset
        ])
        response.write(data)
        Recipe._meta.ordering = ['-created']
        return response

    def create_delete_or_scold(self, model, recipe, request):
        instance = model.objects.filter(recipe=recipe, user=request.user)
        name = model.__name__
        if request.method == 'DELETE' and not instance:
            return Response(
                {'errors': f'This recipe was not on your {name} list.'},
                status=HTTP_400_BAD_REQUEST
            )
        if request.method == 'DELETE':
            instance.delete()
            return Response(status=HTTP_204_NO_CONTENT)
        if instance:
            return Response(
                {'errors': f'This recipe was already on your {name} list.'},
                status=HTTP_400_BAD_REQUEST
            )
        model.objects.create(user=request.user, recipe=recipe)
        serializer = RecipeSmallSerializer(
            recipe,
            context={
                'request': request,
                'format': self.format_kwarg,
                'view': self
            }
        )
        return Response(serializer.data, status=HTTP_201_CREATED)

    @action(
        methods=['post', 'delete'],
        detail=True,
        permission_classes=[IsAuthenticated]
    )
    def favorite(self, request, pk):
        recipe = get_object_or_404(Recipe, id=pk)
        return self.create_delete_or_scold(Favorite, recipe, request)

    @action(
        methods=['post', 'delete'],
        detail=True,
        permission_classes=[IsAuthenticated]
    )
    def shopping_cart(self, request, pk):
        recipe = get_object_or_404(Recipe, id=pk)
        return self.create_delete_or_scold(ShoppingCart, recipe, request)


class IngredientViewSet(ModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = [DjangoFilterBackend, ]
    filterset_class = IngredientFilter
    http_method_names = ['get', ]
    pagination_class = None


class TagViewSet(ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    http_method_names = ['get', ]
    pagination_class = None
