from rest_framework import permissions


class IsAuthorOrReadOnly(permissions.IsAuthenticatedOrReadOnly):
    """Изменять и удалять запись может только её автор."""

    def has_object_permission(self, request, view, record):
        return (
            request.method in permissions.SAFE_METHODS
            or record.author == request.user
        )
