"""
Database router for the authentication app.

This router directs database operations for the `authentication` app to the
`authentication_shard` database.
"""

from typing import Any, Optional

from django.db.models import Model


class AuthenticationRouter:
    """
    Routes database operations for the authentication app.

    Ensures all operations for the `authentication` app are directed to the
    `authentication_shard` database.
    """

    app_label: str = "authentication"
    db_name: str = "authentication_shard"

    def db_for_read(self, model: Model, **hints: Any) -> Optional[str]:
        """
        Direct read operations for authentication models to the `authentication_shard`.

        Args:
            model (Model): The model class for which the read operation is being performed.
            **hints (Any): Additional hints that may influence routing.

        Returns:
            Optional[str]: The database alias to use for read operations,
            or None to fallback to the default.
        """
        if model._meta.app_label == self.app_label:
            return self.db_name
        return None

    def db_for_write(self, model: Model, **hints: Any) -> Optional[str]:
        """
        Direct write operations for authentication models to the `authentication_shard`.

        Args:
            model (Model): The model class for which the write operation is being performed.
            **hints (Any): Additional hints that may influence routing.

        Returns:
            Optional[str]: The database alias to use for write operations,
            or None to fallback to the default.
        """
        if model._meta.app_label == self.app_label:
            return self.db_name
        return None

    def allow_relation(self, obj1: Model, obj2: Model,
                       **hints: Any) -> Optional[bool]:
        """
        Allow relations within the `authentication` app or between apps sharing the same database.

        Args:
            obj1 (Model): The first model instance.
            obj2 (Model): The second model instance.
            **hints (Any): Additional hints that may influence relation permissions.

        Returns:
            Optional[bool]: True if the relation is allowed, False otherwise,
            or None to fallback to the default behavior.
        """
        if obj1._state.db in [self.db_name, "default"] and obj2._state.db in [
            self.db_name,
            "default",
        ]:
            return True
        return None

    def allow_migrate(
        self, db: str, app_label: str, model_name: Optional[str] = None, **hints: Any
    ) -> Optional[bool]:
        """
        Ensure migrations for the `authentication` app go to the `authentication_shard`.

        Args:
            db (str): The database alias where migration is being attempted.
            app_label (str): The app label of the model being migrated.
            model_name (Optional[str]): The name of the model being migrated.
            **hints (Any): Additional hints that may influence migration routing.

        Returns:
            Optional[bool]: True if migration is allowed on the specified database,
            False otherwise, or None to fallback.
        """
        if app_label == self.app_label:
            return db == self.db_name
        return None
