from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import Group
from django.db.models import Count
from django.utils.safestring import mark_safe

from .models import (
    Favorite,
    Product,
    Recipe,
    RecipeProduct,
    ShoppingCart,
    Subscription,
    Tag,
    User,
)

admin.site.unregister(Group)


class HasRelatedFilter(admin.SimpleListFilter):
    """Базовый фильтр «есть связанные записи / нет»."""

    relation = None
    LOOKUP_CHOICES = (('1', 'Есть'), ('0', 'Нет'))

    def lookups(self, request, model_admin):
        return self.LOOKUP_CHOICES

    def queryset(self, request, records):
        if self.value() == '1':
            return records.filter(
                **{f'{self.relation}__isnull': False}
            ).distinct()
        if self.value() == '0':
            return records.filter(**{f'{self.relation}__isnull': True})
        return records


class HasRecipesFilter(HasRelatedFilter):
    title = 'есть рецепты'
    parameter_name = 'has_recipes'
    relation = 'recipes'


class InRecipesFilter(HasRelatedFilter):
    title = 'есть в рецептах'
    parameter_name = 'in_recipes'
    relation = 'recipes'


class HasSubscriptionsFilter(HasRelatedFilter):
    title = 'есть подписки'
    parameter_name = 'has_subscriptions'
    relation = 'subscriptions'


class HasSubscribersFilter(HasRelatedFilter):
    title = 'есть подписчики'
    parameter_name = 'has_subscribers'
    relation = 'author_subscriptions'


class CookingTimeFilter(admin.SimpleListFilter):
    """Гистограмма из трёх бинов с порогами по текущим рецептам."""

    title = 'время готовки'
    parameter_name = 'cooking_time'
    ranges = {}

    def lookups(self, request, model_admin):
        times = sorted(
            Recipe.objects.values_list('cooking_time', flat=True)
        )
        if len(set(times)) < 3:
            return ()
        fast, medium = times[len(times) // 3], times[len(times) * 2 // 3]
        self.ranges = {
            'fast': (0, fast - 1),
            'medium': (fast, medium - 1),
            'long': (medium, 10 ** 10),
        }
        names = {
            'fast': f'быстрее {fast} мин',
            'medium': f'быстрее {medium} мин',
            'long': f'дольше {medium} мин',
        }
        counts = {
            value: Recipe.objects.filter(
                cooking_time__range=time_range
            ).count()
            for value, time_range in self.ranges.items()
        }
        return [
            (value, f'{names[value]} ({counts[value]})')
            for value in self.ranges
        ]

    def queryset(self, request, recipes):
        if self.value() not in self.ranges:
            return recipes
        return recipes.filter(
            cooking_time__range=self.ranges[self.value()]
        )


class RecipesCountMixin:
    """Показ числа рецептов — общий для тегов, продуктов и пользователей."""

    list_display = ('recipes_count',)

    @admin.display(description='Рецептов')
    def recipes_count(self, record):
        return record.recipes.count()


class RecipeProductInline(admin.TabularInline):
    model = RecipeProduct
    min_num = 1
    extra = 0


@admin.register(Tag)
class TagAdmin(RecipesCountMixin, admin.ModelAdmin):
    list_display = ('id', 'name', 'slug', *RecipesCountMixin.list_display)
    search_fields = ('name', 'slug')
    list_filter = (InRecipesFilter,)


@admin.register(Product)
class ProductAdmin(RecipesCountMixin, admin.ModelAdmin):
    list_display = (
        'id',
        'name',
        'measurement_unit',
        *RecipesCountMixin.list_display,
    )
    search_fields = ('name', 'measurement_unit')
    list_filter = ('measurement_unit', InRecipesFilter)


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'name',
        'cooking_time_display',
        'author',
        'favorites_count',
        'products_display',
        'tags_display',
        'image_display',
    )
    search_fields = (
        'name',
        'author__username',
        'author__email',
        'tags__name',
        'products__name',
    )
    list_filter = ('tags', 'author', CookingTimeFilter)
    inlines = (RecipeProductInline,)
    fields = (
        'name',
        'author',
        'text',
        'cooking_time',
        'tags',
        ('image_display', 'image'),
        'favorites_count',
    )
    readonly_fields = ('favorites_count', 'image_display')

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            favorites_total=Count('favorites', distinct=True)
        ).select_related('author').prefetch_related(
            'tags', 'recipe_products__product'
        )

    @admin.display(
        description=mark_safe('Время<br>(мин)'), ordering='cooking_time'
    )
    def cooking_time_display(self, recipe):
        return recipe.cooking_time

    @admin.display(description='В избранном')
    def favorites_count(self, recipe):
        return recipe.favorites_total

    @admin.display(description='Продукты')
    @mark_safe
    def products_display(self, recipe):
        return '<br>'.join(
            f'{item.product.name} ({item.product.measurement_unit}) — '
            f'{item.amount}'
            for item in recipe.recipe_products.all()
        )

    @admin.display(description='Теги')
    @mark_safe
    def tags_display(self, recipe):
        return '<br>'.join(tag.name for tag in recipe.tags.all())

    @admin.display(description='Картинка')
    @mark_safe
    def image_display(self, recipe):
        if not recipe.image:
            return ''
        return f'<img src="{recipe.image.url}" height="60">'


@admin.register(RecipeProduct)
class RecipeProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'recipe', 'product', 'amount')
    search_fields = ('recipe__name', 'product__name')


@admin.register(Favorite, ShoppingCart)
class UserRecipeRelationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'recipe')
    search_fields = ('user__username', 'recipe__name')


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'author')
    search_fields = ('user__username', 'author__username')


@admin.register(User)
class UserAdmin(RecipesCountMixin, DjangoUserAdmin):
    list_display = (
        'id',
        'username',
        'full_name',
        'email',
        'avatar_display',
        *RecipesCountMixin.list_display,
        'subscriptions_count',
        'subscribers_count',
    )
    search_fields = ('email', 'username', 'first_name', 'last_name')
    list_filter = (
        HasRecipesFilter,
        HasSubscriptionsFilter,
        HasSubscribersFilter,
        *DjangoUserAdmin.list_filter,
    )
    fieldsets = (
        *DjangoUserAdmin.fieldsets,
        ('Аватар', {'fields': (('avatar_display', 'avatar'),)}),
    )
    readonly_fields = ('avatar_display',)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            subscriptions_total=Count('subscriptions', distinct=True),
            subscribers_total=Count('author_subscriptions', distinct=True),
        )

    @admin.display(description='ФИО')
    def full_name(self, user):
        return f'{user.first_name} {user.last_name}'

    @admin.display(description='Аватар')
    @mark_safe
    def avatar_display(self, user):
        if not user.avatar:
            return ''
        return f'<img src="{user.avatar.url}" height="60">'

    @admin.display(description='Подписок')
    def subscriptions_count(self, user):
        return user.subscriptions_total

    @admin.display(description='Подписчиков')
    def subscribers_count(self, user):
        return user.subscribers_total
