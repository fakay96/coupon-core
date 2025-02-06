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

    def db_for_read(self, model, **hints):
        """Route read operations for geodiscounts models."""
        if model._meta.app_label == self.APP_LABEL:
            return self.DB_NAME
        return None

    def db_for_write(self, model, **hints):
        """Route write operations for geodiscounts models."""
        if model._meta.app_label == self.APP_LABEL:
            return self.DB_NAME
        return None

    def allow_relation(self, obj1, obj2, **hints):
        """Allow relations if either object is in the geodiscounts app."""
        if (
            obj1._meta.app_label == self.APP_LABEL
            or obj2._meta.app_label == self.APP_LABEL
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
            if db != self.DB_NAME:
                return False
                
            # Check for GIS compatibility if we have access to the schema editor
            schema_editor = hints.get('schema_editor')
            if schema_editor:
                return self._check_gis_compatibility(schema_editor)
                
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