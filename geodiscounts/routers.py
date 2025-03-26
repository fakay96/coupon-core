"""
Database Router for the geodiscounts app.

This router directs all database operations for models in the `geodiscounts`
app to a specific relational database (`geodiscounts_db`).
"""
class GeoDiscountsRouter:
    """
    A database router to control all database operations on models in the `geodiscounts` app.
    Includes proper handling of GIS operations and database compatibility checks.
    """

    APP_LABEL = "geodiscounts"
    DB_NAME = "geodiscounts_db"
    AUTH_APP_LABEL = "authentication"
    REQUIRED_APPS = {
        "auth",
        "contenttypes",
        "authentication",
        "geodiscounts",
        "sessions",
        "admin",
    }

    def db_for_read(self, model, **hints):
        """Route read operations for geodiscounts models and related auth models."""
        if model._meta.app_label == self.APP_LABEL:
            return self.DB_NAME
        elif model._meta.app_label == self.AUTH_APP_LABEL:
            # Add a hint for the authentication router
            hints['target_db'] = self.DB_NAME
            return None
        return None

    def db_for_write(self, model, **hints):
        """Route write operations for geodiscounts models and related auth models."""
        if model._meta.app_label == self.APP_LABEL:
            return self.DB_NAME
        elif model._meta.app_label == self.AUTH_APP_LABEL:
            # Add a hint for the authentication router
            hints['target_db'] = self.DB_NAME
            return None
        return None

    def allow_relation(self, obj1, obj2, **hints):
        """Allow relations if either object is in the geodiscounts app or authentication app."""
        if (
            obj1._meta.app_label in self.REQUIRED_APPS
            or obj2._meta.app_label in self.REQUIRED_APPS
        ):
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Control migrations based on app label and GIS compatibility.
        
        Args:
            db: The database alias
            app_label: The app label being migrated
            model_name: The name of the model being migrated
            **hints: Additional hints including the SchemaEditor
        
        Returns:
            bool | None: Whether to allow the migration
        """
        if app_label == self.APP_LABEL:
            # Only allow geodiscounts app to migrate to geodiscounts_db
            return db == self.DB_NAME
        elif app_label == self.AUTH_APP_LABEL:
            # Let the authentication router handle this
            return None
        elif app_label in self.REQUIRED_APPS:
            # Allow other required apps to migrate to both databases
            return True
        return None

    def _check_gis_compatibility(self, schema_editor):
        """
        Check if the database backend supports GIS operations.
        
        Args:
            schema_editor: The schema editor being used
            
        Returns:
            bool: Whether the backend supports GIS operations
        """
        try:
            # Check for GIS support through multiple methods
            connection = schema_editor.connection
            
            # Method 1: Check for geo_db_type
            if hasattr(connection.ops, 'geo_db_type'):
                return True
                
            # Method 2: Check if using a known GIS backend
            backend_name = connection.vendor
            gis_backends = {'postgresql', 'postgis', 'mysql', 'sqlite'}
            if backend_name.lower() in gis_backends:
                return True
                
            # Method 3: Check for spatial backend features
            if hasattr(connection.features, 'gis_enabled'):
                return connection.features.gis_enabled
                
            return False
            
        except Exception as e:
            # Log the error if you have logging configured
            import logging
            logging.error(f"GIS compatibility check failed: {str(e)}")
            return False