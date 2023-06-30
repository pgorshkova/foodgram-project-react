from django.contrib import admin
from .models import Ingredient, Recipe, Tag


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ['name', 'author', 'created', 'number_of_additions']
    search_fields = ['name', 'author__username', '^tags__name']
    list_filter = ['author', 'name', 'tags']
    readonly_fields = ['number_of_additions']

    def number_of_additions(self, obj: Recipe):
        return len(obj.shopping_users.all())


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'measure']
    search_fields = ['name', 'measure']
    list_filter = ['name', ]


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name', 'color', 'slug']
    search_fields = ['name', 'colow', 'slug']
    list_filter = ['name', 'color', 'slug']
