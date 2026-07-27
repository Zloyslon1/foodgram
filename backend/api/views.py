from django.db.models import Sum
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from djoser.views import UserViewSet as DjoserUserViewSet
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from recipes.models import (
    Favorite,
    Product,
    Recipe,
    RecipeProduct,
    ShoppingCart,
    Subscription,
    Tag,
    User,
)
from recipes.shopping_list import render_shopping_list
from .filters import ProductFilter, RecipeFilter
from .permissions import IsAuthorOrReadOnly
from .serializers import (
    AvatarSerializer,
    ProductSerializer,
    RecipeReadSerializer,
    RecipeShortReadSerializer,
    RecipeWriteSerializer,
    TagSerializer,
    UserWithRecipesSerializer,
)


class UserViewSet(DjoserUserViewSet):
    """Пользователи: регистрация, профили, аватар, подписки."""

    @action(('get',), detail=False, permission_classes=(IsAuthenticated,))
    def me(self, request, *args, **kwargs):
        return super().me(request, *args, **kwargs)

    @action(
        ('put', 'delete'),
        detail=False,
        url_path='me/avatar',
        permission_classes=(IsAuthenticated,),
    )
    def avatar(self, request):
        user = request.user
        if request.method == 'DELETE':
            user.avatar.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        serializer = AvatarSerializer(user, data=request.data)
        serializer.is_valid(raise_exception=True)
        user.avatar.delete(save=False)
        serializer.save()
        return Response(serializer.data)

    @action(('get',), detail=False, permission_classes=(IsAuthenticated,))
    def subscriptions(self, request):
        return self.get_paginated_response(
            UserWithRecipesSerializer(
                self.paginate_queryset(
                    User.objects.filter(
                        author_subscriptions__user=request.user
                    ).prefetch_related('recipes')
                ),
                many=True,
                context=self.get_serializer_context(),
            ).data
        )

    @action(
        ('post', 'delete'),
        detail=True,
        permission_classes=(IsAuthenticated,),
    )
    def subscribe(self, request, id=None):
        if request.method == 'DELETE':
            get_object_or_404(
                Subscription, user=request.user, author_id=id
            ).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        author = get_object_or_404(User, pk=id)
        if author == request.user:
            raise ValidationError('Нельзя подписаться на самого себя.')
        _, created = Subscription.objects.get_or_create(
            user=request.user, author=author
        )
        if not created:
            raise ValidationError(
                f'Вы уже подписаны на автора {author.username}.'
            )
        return Response(
            UserWithRecipesSerializer(
                author, context=self.get_serializer_context()
            ).data,
            status=status.HTTP_201_CREATED,
        )


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (AllowAny,)
    pagination_class = None


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = (AllowAny,)
    pagination_class = None
    filterset_class = ProductFilter


class RecipeViewSet(viewsets.ModelViewSet):
    """Рецепты: CRUD, избранное, корзина, короткая ссылка."""

    queryset = Recipe.objects.select_related('author').prefetch_related(
        'tags', 'recipe_products__product'
    )
    permission_classes = (IsAuthorOrReadOnly,)
    filterset_class = RecipeFilter

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return RecipeWriteSerializer
        return RecipeReadSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(
        ('get',),
        detail=True,
        url_path='get-link',
        permission_classes=(AllowAny,),
    )
    def get_link(self, request, pk=None):
        if not Recipe.objects.filter(pk=pk).exists():
            raise NotFound(f'Рецепт с id {pk} не найден.')
        return Response({
            'short-link': request.build_absolute_uri(
                reverse('recipes:short-link', args=(pk,))
            )
        })

    def _manage_relation(self, request, pk, model):
        """Добавление рецепта в избранное или корзину и удаление из них."""
        if request.method == 'DELETE':
            get_object_or_404(
                model, user=request.user, recipe_id=pk
            ).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        recipe = self.get_object()
        _, created = model.objects.get_or_create(
            user=request.user, recipe=recipe
        )
        if not created:
            raise ValidationError(
                f'Рецепт «{recipe.name}» уже добавлен в '
                f'{model._meta.verbose_name}.'
            )
        return Response(
            RecipeShortReadSerializer(
                recipe, context=self.get_serializer_context()
            ).data,
            status=status.HTTP_201_CREATED,
        )

    @action(
        ('post', 'delete'),
        detail=True,
        permission_classes=(IsAuthenticated,),
    )
    def favorite(self, request, pk=None):
        return self._manage_relation(request, pk, Favorite)

    @action(
        ('post', 'delete'),
        detail=True,
        permission_classes=(IsAuthenticated,),
    )
    def shopping_cart(self, request, pk=None):
        return self._manage_relation(request, pk, ShoppingCart)

    @action(
        ('get',),
        detail=False,
        permission_classes=(IsAuthenticated,),
    )
    def download_shopping_cart(self, request):
        return FileResponse(
            render_shopping_list(
                RecipeProduct.objects
                .filter(recipe__shoppingcarts__user=request.user)
                .values('product__name', 'product__measurement_unit')
                .annotate(total=Sum('amount'))
                .order_by('product__name'),
                Recipe.objects
                .filter(shoppingcarts__user=request.user)
                .select_related('author'),
            ),
            as_attachment=True,
            filename='shopping_list.txt',
            content_type='text/plain; charset=utf-8',
        )
