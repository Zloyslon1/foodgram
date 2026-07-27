from rest_framework.pagination import PageNumberPagination

DEFAULT_PAGE_SIZE = 6


class LimitPageNumberPagination(PageNumberPagination):
    """Пагинация с настройкой размера страницы через параметр limit."""

    page_size = DEFAULT_PAGE_SIZE
    page_size_query_param = 'limit'
