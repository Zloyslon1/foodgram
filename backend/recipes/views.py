from django.shortcuts import get_object_or_404, redirect

from .models import Recipe


def short_link_redirect(request, short_code):
    """Редирект с короткой ссылки на страницу рецепта."""
    recipe = get_object_or_404(Recipe, short_code=short_code)
    return redirect(f'/recipes/{recipe.pk}/')
