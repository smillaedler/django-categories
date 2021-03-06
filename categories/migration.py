from django.db import models, DatabaseError
from django.core.exceptions import ImproperlyConfigured
from .fields import CategoryM2MField, CategoryFKField
from .models import Category
from .settings import FIELD_REGISTRY


def migrate_app(app, *args, **kwargs):
    """
    Migrate all models of this app registered
    """
    try:
        from south.db import db
    except ImportError:
        raise ImproperlyConfigured("South must be installed for this command to work")

    # pull the information from the registry
    if not isinstance(app, basestring):
        return
    fields = [fld for fld in FIELD_REGISTRY.keys() if fld.startswith(app)]

    # call the south commands to add the fields/tables
    for fld in fields:
        app_name, model_name, field_name = fld.split('.')

        # Table is typically appname_modelname, but it could be different
        #   always best to be sure.
        mdl = models.get_model(app_name, model_name)

        if isinstance(FIELD_REGISTRY[fld], CategoryFKField):
            print "Adding ForeignKey %s to %s" % (field_name, model_name)
            try:
                db.start_transaction()
                table_name = mdl._meta.db_table
                FIELD_REGISTRY[fld].default = -1
                db.add_column(table_name, field_name, FIELD_REGISTRY[fld], keep_default=False)
                db.commit_transaction()
            except DatabaseError, e:
                db.rollback_transaction()
                if "already exists" in str(e):
                    print "Already exists"
                else:
                    raise e
        elif isinstance(FIELD_REGISTRY[fld], CategoryM2MField):
            print "Adding Many2Many table between %s and %s" % (model_name, 'category')
            table_name = "%s_%s" % (mdl._meta.db_table, 'categories')
            try:
                db.start_transaction()
                db.create_table(table_name, (
                    ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
                    (model_name, models.ForeignKey(mdl, null=False)),
                    ('category', models.ForeignKey(Category, null=False))
                ))
                db.create_unique(table_name, ['%s_id' % model_name, 'category_id'])
                db.commit_transaction()
            except DatabaseError, e:
                db.rollback_transaction()
                if "already exists" in str(e):
                    print "Already exists"
                else:
                    raise e


def drop_field(app_name, model_name, field_name):
    """
    Drop the given field from the app's model
    """
    # Table is typically appname_modelname, but it could be different
    #   always best to be sure.
    try:
        from south.db import db
    except ImportError:
        raise ImproperlyConfigured("South must be installed for this command to work")
    mdl = models.get_model(app_name, model_name)

    fld = "%s.%s.%s" % (app_name, model_name, field_name)

    if isinstance(FIELD_REGISTRY[fld], CategoryFKField):
        print "Dropping ForeignKey %s from %s" % (field_name, model_name)
        try:
            db.start_transaction()
            table_name = mdl._meta.db_table
            db.delete_column(table_name, field_name)
            db.commit_transaction()
        except DatabaseError, e:
            db.rollback_transaction()
            raise e
    elif isinstance(FIELD_REGISTRY[fld], CategoryM2MField):
        print "Dropping Many2Many table between %s and %s" % (model_name, 'category')
        table_name = "%s_%s" % (mdl._meta.db_table, 'categories')
        try:
            db.start_transaction()
            db.delete_table(table_name, cascade=False)
            db.commit_transaction()
        except DatabaseError, e:
            db.rollback_transaction()
            raise e

try:
    from south.signals import post_migrate
    post_migrate.connect(migrate_app)
except ImportError:
    pass
