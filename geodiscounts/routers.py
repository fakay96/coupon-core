"""
Database Router for the geodiscounts and authentication apps.

This router directs all database operations for models in the `geodiscounts`
app to a specific relational database (`geodiscounts_db`), and all operations
for the `authentication` app to `authentication_shard`. It enforces strict
database isolation and prevents cross-database relationships.
"""

class GeoDiscountsRouter:
    """
    A database router to control all database operations on models in the
    `geodiscounts` and `authentication` apps, ensuring each app only interacts
    with its designated database shard.

    - Routes all geodiscounts models to `geodiscounts_db`.
    - Routes all authentication models to `authentication_shard`.
    - Routes shared Django apps (auth, admin, contenttypes, sessions) to `default`.
    - Prevents cross-database relations and migrations.
    """

    GEODISCOUNTS_APPS = {'geodiscounts'}
    AUTH_APP = {'authentication'}
    SHARED_APPS = {'admin', 'auth', 'contenttypes', 'sessions'}

    def db_for_read(self, model, **hints):
        """
        Directs read operations for models to the correct database.

        Args:
            model: The model class being queried.
            **hints: Additional hints.

        Returns:
            str | None: The database alias or None to fall back to default.
        """
        if model._meta.app_label in self.GEODISCOUNTS_APPS:
            return 'geodiscounts_db'
        if model._meta.app_label in self.AUTH_APP:
            return 'authentication_shard'
        return 'default'

    def db_for_write(self, model, **hints):
        """
        Directs write operations for models to the correct database.

        Args:
            model: The model class being written to.
            **hints: Additional hints.

        Returns:
            str | None: The database alias or None to fall back to default.
        """
        if model._meta.app_label in self.GEODISCOUNTS_APPS:
            return 'geodiscounts_db'
        if model._meta.app_label in self.AUTH_APP:
            return 'authentication_shard'
        return 'default'

    def allow_relation(self, obj1, obj2, **hints):
        """
        Only allow relations within the same database.

        Args:
            obj1: The first model instance.
            obj2: The second model instance.
            **hints: Additional hints.

        Returns:
            bool | None: True if allowed, False if not, None to fall back to default.
        """
        db1 = self.db_for_read(obj1._meta.model)
        db2 = self.db_for_read(obj2._meta.model)
        return db1 == db2

    def allow_migrate(self, db, app_label, **hints):
        """
        Ensure each app only migrates to its designated database.

        Args:
            db: The database alias.
            app_label: The app label being migrated.
            **hints: Additional hints.

        Returns:
            bool | None: True if migration is allowed, False if not, None to fall back to default.
        """
        if app_label in self.GEODISCOUNTS_APPS:
            return db == 'geodiscounts_db'
        if app_label in self.AUTH_APP:
            return db == 'authentication_shard'
        if app_label in self.SHARED_APPS:
            return db == 'default'
        return None
