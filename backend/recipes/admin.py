from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
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


class HasRelatedFilter(admin.SimpleListFilter):
    """Базовый фильтр «есть связанные записи / нет»."""

    relation = None

    def lookups(self, request, model_admin):
        return (('1', 'Есть'), ('0', 'Нет'))

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

    @staticmethod
    def thresholds():
        times = sorted(
            Recipe.objects.values_list('cooking_time', flat=True)
        )
        if len(set(times)) < 3:
            return None
        fast, medium = times[len(times) // 3], times[len(times) * 2 // 3]
        return None if fast == medium else (fast, medium)

    def bins(self):
        thresholds = self.thresholds()
        if thresholds is None:
            return {}
        fast, medium = thresholds
        return {
            'fast': (f'быстрее {fast} мин', {'cooking_time__lt': fast}),
            'medium': (
                f'быстрее {medium} мин',
                {'cooking_time__range': (fast, medium - 1)},
            ),
            'long': (f'дольше {medium} мин', {'cooking_time__gte': medium}),
        }

    def lookups(self, request, model_admin):
        return [
            (
                value,
                f'{label} ({Recipe.objects.filter(**condition).count()})',
            )
            for value, (label, condition) in self.bins().items()
        ]

    def queryset(self, request, recipes):
        bin_ = self.bins().get(self.value())
        return recipes if bin_ is None else recipes.filter(**bin_[1])


class RecipesCountMixin:
    """Показ числа рецептов — общий для тегов и продуктов."""

    @admin.display(description='Рецептов')
    def recipes_count(self, tag_or_product):
        return tag_or_product.recipes.count()


class RecipeProductInline(admin.TabularInline):
    model = RecipeProduct
    min_num = 1
    extra = 0


@admin.register(Tag)
class TagAdmin(RecipesCountMixin, admin.ModelAdmin):
    list_display = ('id', 'name', 'slug', 'recipes_count')
    search_fields = ('name', 'slug')
    list_filter = (InRecipesFilter,)


@admin.register(Product)
class ProductAdmin(RecipesCountMixin, admin.ModelAdmin):
    list_display = ('id', 'name', 'measurement_unit', 'recipes_count')
    search_fields = ('name', 'measurement_unit')
    list_filter = ('measurement_unit', InRecipesFilter)


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'name',
        'cooking_time',
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
    readonly_fields = ('favorites_count',)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            favorites_total=Count('favorites', distinct=True)
        ).select_related('author').prefetch_related(
            'tags', 'recipe_products__product'
        )

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
class UserAdmin(DjangoUserAdmin):
    list_display = (
        'id',
        'username',
        'full_name',
        'email',
        'avatar_display',
        'recipes_count',
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
        ('Аватар', {'fields': ('avatar',)}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            recipes_total=Count('recipes', distinct=True),
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

    @admin.display(description='Рецептов')
    def recipes_count(self, user):
        return user.recipes_total

    @admin.display(description='Подписок')
    def subscriptions_count(self, user):
        return user.subscriptions_total

    @admin.display(description='Подписчиков')
    def subscribers_count(self, user):
        return user.subscribers_total
