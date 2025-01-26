"""
Database Router for the geodiscounts app.

This router directs all database operations for models in the `geodiscounts`
app to a specific relational database (`geodiscounts_db`).
"""


class GeoDiscountsRouter:
    """
    A database router to control all database operations on models in the `geodiscounts` app.
    """

    APP_LABEL = "geodiscounts"  # The app label for geodiscounts models
    DB_NAME = (
        "geodiscounts_db"  # The relational database alias for geodiscounts metadata
    )

    def db_for_read(self, model, **hints):
        """
        Route read operations for geodiscounts models to the geodiscounts database.

        Args:
            model: The model being queried.
            **hints: Additional query hints.

        Returns:
            str | None: The database alias for reading.
        """
        if model._meta.app_label == self.APP_LABEL:
            return self.DB_NAME
        return None

    def db_for_write(self, model, **hints):
        """
        Route write operations for geodiscounts models to the geodiscounts database.

        Args:
            model: The model being written to.
            **hints: Additional query hints.

        Returns:
            str | None: The database alias for writing.
        """
        if model._meta.app_label == self.APP_LABEL:
            return self.DB_NAME
        return None

    def allow_relation(self, obj1, obj2, **hints):
        """
        Allow relations if both objects are in the geodiscounts database.

        Args:
            obj1: The first model instance.
            obj2: The second model instance.
            **hints: Additional query hints.

        Returns:
            bool | None: Whether the relation is allowed.
        """
        if (
            obj1._meta.app_label == self.APP_LABEL
            or obj2._meta.app_label == self.APP_LABEL
        ):
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Ensure migrations for geodiscounts models are applied only to the geodiscounts database.

        Args:
            db: The database alias.
            app_label: The app label being migrated.
            model_name: The name of the model being migrated.
            **hints: Additional query hints.

        Returns:
            bool: Whether the migration is allowed.
        """
        if app_label == self.APP_LABEL:
            return db == self.DB_NAME
        return None
