"""
Database router for routing authentication and related apps (admin, auth, sessions, contenttypes)
to the authentication_shard database.
"""

from typing import Any, Optional, Set
from django.db.models import Model

class AuthenticationRouter:
    """
    Routes database operations for the authentication app and related system apps
    (admin, auth, sessions, contenttypes) to the authentication_shard database.
    """

    target_apps: Set[str] = {"authentication", "admin", "auth", "sessions", "contenttypes","authtoken","socialaccount","account"}
    db_name: str = "authentication_shard"
    allowed_dbs: Set[str] = {"authentication_shard", "geodiscounts_db"}

    def db_for_read(self, model: Model, **hints: Any) -> Optional[str]:
        """
        Direct read operations for target apps to the authentication_shard database.

        Args:
            model (Model): The model class to be read.
            **hints (Any): Additional hints.

        Returns:
            Optional[str]: The database alias if the model belongs to a target app; otherwise, None.
        """
        if model._meta.app_label in self.target_apps:
            # Check if there's a specific database hint
            if 'target_db' in hints:
                return hints['target_db']
            return self.db_name
        return None

    def db_for_write(self, model: Model, **hints: Any) -> Optional[str]:
        """
        Direct write operations for target apps to the authentication_shard database.

        Args:
            model (Model): The model class to be written.
            **hints (Any): Additional hints.

        Returns:
            Optional[str]: The database alias if the model belongs to a target app; otherwise, None.
        """
        if model._meta.app_label in self.target_apps:
            # Check if there's a specific database hint
            if 'target_db' in hints:
                return hints['target_db']
            return self.db_name
        return None

    def allow_relation(self, obj1: Model, obj2: Model, **hints: Any) -> Optional[bool]:
        """
        Allow relations if both objects are in either the authentication_shard or the default database.

        Args:
            obj1 (Model): The first model instance.
            obj2 (Model): The second model instance.
            **hints (Any): Additional hints.

        Returns:
            Optional[bool]: True if the relation is allowed, False otherwise, or None to use the default.
        """
        if obj1._state.db in self.allowed_dbs and obj2._state.db in self.allowed_dbs:
            return True
        return None

    def allow_migrate(
        self, db: str, app_label: str, model_name: Optional[str] = None, **hints: Any
    ) -> Optional[bool]:
        """
        Allow migrations for target apps on both authentication_shard and geodiscounts_db databases.

        Args:
            db (str): The database alias where migration is being attempted.
            app_label (str): The app label of the model being migrated.
            model_name (Optional[str]): The name of the model being migrated.
            **hints (Any): Additional hints.

        Returns:
            Optional[bool]: True if migration is allowed on the specified database, False otherwise,
                            or None to fallback to default behavior.
        """
        if app_label in self.target_apps:
            return db in self.allowed_dbs
        return None
