from __future__ import unicode_literals

from decimal import Decimal
from datetime import datetime

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.fields import FieldDoesNotExist
from django.utils import datetime_safe

try:
    from django.utils.encoding import force_text
except ImportError:
    from django.utils.encoding import force_unicode as force_text


class Widget(object):
    """
    Widget takes care of converting between import and export representations.

    Widget objects have two functions:

    * converts object field value to export representation

    * converts import value and converts it to appropriate python
      representation
    """
    def clean(self, value):
        """
        Returns appropriate python objects for import value.
        """
        return value

    def render(self, value):
        """
        Returns export representation of python value.
        """
        return force_text(value)


class IntegerWidget(Widget):
    """
    Widget for converting integer fields.
    """

    def clean(self, value):
        if not value:
            return None
        return int(value)


class DecimalWidget(Widget):
    """
    Widget for converting decimal fields.
    """

    def clean(self, value):
        if not value:
            return None
        return Decimal(value)


class CharWidget(Widget):
    """
    Widget for converting text fields.
    """

    def render(self, value):
        return force_text(value)


class BooleanWidget(Widget):
    """
    Widget for converting boolean fields.
    """
    TRUE_VALUES = ["1", 1]
    FALSE_VALUE = "0"

    def render(self, value):
        return self.TRUE_VALUES[0] if value else self.FALSE_VALUE

    def clean(self, value):
        return True if value in self.TRUE_VALUES else False


class DateWidget(Widget):
    """
    Widget for converting date fields.

    Takes optional ``format`` parameter.
    """

    def __init__(self, format=None):
        if format is None:
            format = "%Y-%m-%d"
        self.format = format

    def clean(self, value):
        if not value:
            return None
        return datetime.strptime(value, self.format).date()

    def render(self, value):
        try:
            return value.strftime(self.format)
        except:
            return datetime_safe.new_date(value).strftime(self.format)


class DateTimeWidget(Widget):
    """
    Widget for converting date fields.

    Takes optional ``format`` parameter.
    """

    def __init__(self, format=None):
        if format is None:
            format = "%Y-%m-%d %H:%M:%S"
        self.format = format

    def clean(self, value):
        if not value:
            return None
        return datetime.strptime(value, self.format)

    def render(self, value):
        return value.strftime(self.format)


class ForeignKeyWidget(Widget):
    """
    Widget for ``ForeignKey`` model field that represent ForeignKey as
    integer value.

    Requires a positional argument: the class to which the field is related.
    """

    def __init__(self, model, *args, **kwargs):
        self.model = model
        super(ForeignKeyWidget, self).__init__(*args, **kwargs)

    def clean(self, value):
        pk = super(ForeignKeyWidget, self).clean(value)

        if pk:
            # Create a cache key from the app label, model name, and pk
            cache_key = '%s_%s_%s' % (
                self.model._meta.app_label,
                self.model._meta.module_name,
                pk.replace(" ", "")
            )

            # print 'cache', cache_key
            obj = cache.get(cache_key)

            # if there's a cached object, return it.
            if obj:
                return obj

            # print 'PK: ', pk

            try:
                # pk = int(pk)
                # look up the object if it's not there and set it in the cache
                # print 'INT PK'
                obj = self.model.objects.get(pk=pk)

            except ValueError:
                # print 'VALUE ERROR'

                try:
                    # print "Lookup by title!"
                    # check for title field exist in model
                    self.model._meta.get_field('title')
                    obj = self.model.objects.get(title=pk)

                except FieldDoesNotExist as e:
                    # print "No title field."
                    pass

            except ObjectDoesNotExist:
                print 'DNE', pk

            cache.set(cache_key, obj)

            # print "FOUND: %s\n" % obj

            # return our object
            return obj

        # print "-----------NO PK"
        return None

    def render(self, value):
        if value is None:
            return ""
        return value.pk


class ManyToManyWidget(Widget):
    """
    Widget for ``ManyToManyField`` model field that represent m2m field
    as comma separated pk values.

    Requires a positional argument: the class to which the field is related.
    """

    def __init__(self, model, *args, **kwargs):
        self.model = model
        super(ManyToManyWidget, self).__init__(*args, **kwargs)

    def clean(self, value):
        if not value:
            return self.model.objects.none()
        ids = value.split(",")
        return self.model.objects.filter(pk__in=ids)

    def render(self, value):
        ids = [str(obj.pk) for obj in value.all()]
        return ",".join(ids)
