import unittest

import django.core.exceptions as dj_exc
import django.db.models as dj_models
from django.conf import settings as dj_settings
from django.test import TestCase

from . import models
from . import settings


class LabelTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        settings.init(dj_settings.BASE_DIR)
        label = models.Label()
        label.save()
        models.Translation(label=label, text='Label', language_code='en').save()
        c = models.Class(label=label, name='A')
        c.save()
        label_p = models.Label()
        label_p.save()
        models.ObjectProperty(host_class=c, type=c, name='P1', label=label_p).save()

    def test_get_label_defined(self):
        self.assertEqual(models.Label.objects.get(class__name='A').get_for_language('en'), 'Label')

    def test_get_label_undefined(self):
        self.assertEqual(models.Label.objects.get(class__name='A').get_for_language('-'), 'A')

    def test_delete_label_error(self):
        with self.assertRaises(dj_models.ProtectedError):
            models.Label.objects.get(class__name='A').delete()
        with self.assertRaises(dj_models.ProtectedError):
            models.Label.objects.get(property__name='P1').delete()

    def test_label_duplicate_use_error(self):
        l1 = models.Label()
        l1.save()
        models.Class(name='Y', label=l1).save()
        with self.assertRaises(dj_exc.ValidationError) as cm:
            models.Class(name='Z', label=l1).save()
        self.assertIn('label', cm.exception.message_dict)


class LabelTranslationTestCase(TestCase):
    def setUp(self):
        super().setUpClass()
        settings.init(dj_settings.BASE_DIR)
        self.label = models.Label()
        self.label.save()
        models.Translation(label=self.label, text='Label 1', language_code='en').save()

    def test_create(self):
        models.Translation(label=self.label, text='Label', language_code='fr').save()
        self.assertEqual(self.label.get_for_language('fr'), 'Label')

    def test_create_duplicate_label_error(self):
        with self.assertRaises(dj_exc.ValidationError):
            models.Translation(label=self.label, text='Label 2', language_code='en').save()

    def test_create_undefined_language(self):
        with self.assertRaises(dj_exc.ValidationError) as cm:
            models.Translation(label=self.label, text='Label 2', language_code='-').save()
        self.assertIn('language_code', cm.exception.message_dict)

    def test_label_null_error(self):
        with self.assertRaises(dj_exc.ValidationError) as cm:
            models.Translation(label=None, text='Label', language_code='fr').save()
        self.assertIn('label', cm.exception.message_dict)

    def test_language_code_null_error(self):
        with self.assertRaises(dj_exc.ValidationError) as cm:
            models.Translation(label=self.label, text='Label', language_code=None).save()
        self.assertIn('language_code', cm.exception.message_dict)

    def test_text_null_error(self):
        with self.assertRaises(dj_exc.ValidationError) as cm:
            models.Translation(label=self.label, text=None, language_code='en').save()
        self.assertIn('text', cm.exception.message_dict)

    def test_text_empty_error(self):
        with self.assertRaises(dj_exc.ValidationError) as cm:
            models.Translation(label=self.label, text='', language_code='en').save()
        self.assertIn('text', cm.exception.message_dict)
        with self.assertRaises(dj_exc.ValidationError) as cm:
            models.Translation(label=self.label, text=' ', language_code='en').save()
        self.assertIn('text', cm.exception.message_dict)


class ClassTestCase(TestCase):
    def setUp(self):
        self.label_a = models.Label()
        self.label_a.save()
        self.class_a = models.Class(name='A', label=self.label_a)
        self.class_a.save()

        self.label_b = models.Label()
        self.label_b.save()
        self.class_b = models.Class(name='B', label=self.label_b)
        self.class_b.save()

        self.label_c = models.Label()
        self.label_c.save()
        self.class_c = models.Class(name='C', label=self.label_c, parent_class=self.class_a)
        self.class_c.save()

        self.label_p1 = models.Label()
        self.label_p1.save()
        self.property_ = models.ObjectProperty(name='P1', label=self.label_p1, host_class=self.class_a,
                                               type=self.class_b)
        self.property_.save()

    def test_parent_class_null(self):
        label = models.Label()
        label.save()
        # Should not raise any errors
        c = models.Class(name='D', label=label, parent_class=None)
        c.save()
        self.assertIsNone(c.parent_class)

    def test_circular_hierarchy(self):
        label = models.Label()
        label.save()
        c = models.Class(name='D', label=label)
        c.parent_class = c
        with self.assertRaises(dj_exc.ValidationError) as cm:
            c.save()
        self.assertIn('parent_class', cm.exception.message_dict)

    def test_name_null_error(self):
        label = models.Label()
        label.save()
        with self.assertRaises(dj_exc.ValidationError) as cm:
            models.Class(name=None, label=label).save()
        self.assertIn('name', cm.exception.message_dict)

    def test_duplicate_name_error(self):
        label = models.Label()
        label.save()
        with self.assertRaises(dj_exc.ValidationError) as cm:
            models.Class(name='A', label=label).save()
        self.assertIn('name', cm.exception.message_dict)

    def test_label_null_error(self):
        with self.assertRaises(dj_exc.ValidationError) as cm:
            models.Class(name='D', label=None).save()
        self.assertIn('label', cm.exception.message_dict)

    def test_geometry_null(self):
        label = models.Label()
        label.save()
        # Should not raise any errors
        c = models.Class(name='D', label=label, geometry_type=None)
        c.save()
        self.assertIsNone(c.geometry_type)

    def test_geometry_invalid_error(self):
        label = models.Label()
        label.save()
        with self.assertRaises(dj_exc.ValidationError) as cm:
            models.Class(name='D', label=label, geometry_type='a').save()
        self.assertIn('geometry_type', cm.exception.message_dict)

    def test_create_inherited_geometry(self):
        l1 = models.Label()
        l1.save()
        c1 = models.Class(name='C1', label=l1, geometry_type='node')
        c1.save()
        l2 = models.Label()
        l2.save()
        c2 = models.Class(name='C2', label=l2, geometry_type='node', parent_class=c1)
        c2.save()
        self.assertEqual(c2.parent_class, c1)
        self.assertEqual(c1.geometry_type, c2.geometry_type)

    def test_create_mismatch_inherited_geometry_error(self):
        l1 = models.Label()
        l1.save()
        c1 = models.Class(name='C1', label=l1, geometry_type='node')
        c1.save()
        l2 = models.Label()
        l2.save()
        with self.assertRaises(dj_exc.ValidationError) as cm:
            models.Class(name='C2', label=l2, geometry_type='polygon', parent_class=c1).save()
        self.assertIn('geometry_type', cm.exception.message_dict)
        with self.assertRaises(dj_exc.ValidationError) as cm:
            models.Class(name='C2', label=l2, geometry_type=None, parent_class=c1).save()
        self.assertIn('geometry_type', cm.exception.message_dict)

    def test_has_property(self):
        self.assertTrue(self.class_a.has_property('P1'))

    def test_has_not_property(self):
        self.assertFalse(self.class_b.has_property('P1'))

    def test_inherited_property(self):
        self.assertTrue(self.class_c.has_property('P1'))

    def test_direct_subtype(self):
        self.assertTrue(self.class_c.is_subtype_of(self.class_a))

    def test_undirect_subtype(self):
        label = models.Label()
        label.save()
        c = models.Class(name='D', label=label, parent_class=self.class_c)
        c.save()
        self.assertTrue(c.is_subtype_of(self.class_a))

    def test_direct_supertype(self):
        self.assertTrue(self.class_a.is_supertype_of(self.class_c))

    def test_undirect_supertype(self):
        label = models.Label()
        label.save()
        c = models.Class(name='D', label=label, parent_class=self.class_c)
        c.save()
        self.assertTrue(self.class_a.is_supertype_of(c))

    def test_delete_class_deletes_label(self):
        self.assertIn(self.label_a, models.Label.objects.all())
        self.class_a.delete()
        self.assertNotIn(self.label_a, models.Label.objects.all())


class PropertyTestCase(TestCase):
    def setUp(self):
        self.label_a = models.Label()
        self.label_a.save()
        self.class_a = models.Class(name='A', label=self.label_a)
        self.class_a.save()

        self.label_b = models.Label()
        self.label_b.save()
        self.class_b = models.Class(name='B', label=self.label_b)
        self.class_b.save()

        self.label_p1 = models.Label()
        self.label_p1.save()
        self.p1 = models.ObjectProperty(host_class=self.class_a, type=self.class_b, name='P1', label=self.label_p1)
        self.p1.save()

    @unittest.skip('Refactoring')
    def test_duplicate_name_for_different_classes(self):
        label = models.Label()
        label.save()
        # Should not raise any errors
        p = models.ObjectProperty(name='P1', label=label, host_class=self.class_b, type=self.class_a)
        p.save()
        self.assertEqual(p.name, 'P1')

    @unittest.skip('Refactoring')
    def test_duplicate_name_for_same_class_error(self):
        label = models.Label()
        label.save()
        with self.assertRaises(dj_exc.ValidationError):
            models.ObjectProperty(name='P1', label=label, host_class=self.class_a, type=self.class_b).save()

    @unittest.skip('Refactoring')
    def test_duplicate_name_for_inherited_class_error(self):
        lc = models.Label()
        lc.save()
        c = models.Class(name='C', label=lc, parent_class=self.class_a)
        c.save()
        lp = models.Label()
        lp.save()
        with self.assertRaises(dj_exc.ValidationError):
            models.ObjectProperty(name='P1', label=lp, host_class=c, type=self.class_b).save()

    def test_delete_property_deletes_label(self):
        self.assertIn(self.label_p1, models.Label.objects.all())
        self.p1.delete()
        self.assertNotIn(self.label_p1, models.Label.objects.all())
