from django.urls import include, path
from rest_framework.routers import SimpleRouter

from .views import IngredientViewSet, RecipeViewSet, TagViewSet, UserViewSet

router = SimpleRouter()

router.register(
    r'recipes', RecipeViewSet, basename='recipes'
)
router.register(
    r'ingredients', IngredientViewSet, basename='ingredients'
)
router.register(
    r'tags', TagViewSet, basename='tags'
)
router.register(
    r'users', UserViewSet, basename='users'
)

authpatterns = [
    path('', include('djoser.urls')),
    path('auth/', include('djoser.urls.authtoken'))
]

urlpatterns = [
    path('', include(router.urls)),
] + authpatterns
