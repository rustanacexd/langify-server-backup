from simple_history.models import (
    HistoricalRecords as BaseHistoricalRecords,
    registered_models,
)

from django.apps import apps


class HistoricalRecords(BaseHistoricalRecords):
    """
    HistoricalRecords with Meta inheritance.
    """

    def get_extra_fields(self, model, fields):
        """
        Extra fields with a backwards relation for the user field.
        """
        model_name = model._meta.model_name
        self.user_related_name = 'historical{}{}s'.format(
            model_name, 'e' if model_name.endswith('s') else ''
        )
        return super().get_extra_fields(model, fields)

    def create_history_model(self, model, inherited):
        """
        Creates a historical model to associate with the model provided.
        """
        # Adapted from simple history ~2.4.0

        attrs = {
            '__module__': self.module,
            '_history_excluded_fields': self.excluded_fields,
        }

        app_module = '%s.models' % model._meta.app_label

        if inherited:
            # inherited use models module
            attrs['__module__'] = model.__module__
        elif model.__module__ != self.module:
            # registered under different app
            attrs['__module__'] = self.module
        elif app_module != self.module:
            # Abuse an internal API because the app registry is loading.
            app = apps.app_configs[model._meta.app_label]
            models_module = app.name
            attrs['__module__'] = models_module

        fields = self.copy_fields(model)
        attrs.update(fields)
        attrs.update(self.get_extra_fields(model, fields))
        attrs.update(
            Meta=type(
                'Meta',
                tuple(
                    base.Meta for base in self.bases if hasattr(base, 'Meta')
                ),
                self.get_meta_options(model),
            )
        )
        if self.table_name is not None:
            attrs['Meta'].db_table = self.table_name
        name = 'Historical%s' % model._meta.object_name
        registered_models[model._meta.db_table] = model
        return type(name, self.bases, attrs)
