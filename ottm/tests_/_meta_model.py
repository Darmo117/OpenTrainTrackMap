import django.core.exceptions as dj_exc
from django.test import TestCase

from .. import data_model as m


# region UnitType
class UnitTypeTestCase(TestCase):
    def test_label_not_unique_error(self):
        def aux():
            u1 = m.UnitType(
                label='foo',
            )
            u1.full_clean()
            u1.save()
            u2 = m.UnitType(
                label='foo',
            )
            u2.full_clean()
            u2.save()

        self.assertRaises(dj_exc.ValidationError, aux)


class UnitTypeTranslationTestCase(TestCase):
    def setUp(self):
        dtf = m.DateTimeFormat(
            format='%d/%m/%y',
        )
        dtf.full_clean()
        dtf.save()
        lang = m.Language(
            code='en',
            name='English',
            writing_direction='ltr',
            available_for_ui=True,
            default_datetime_format=dtf,
        )
        lang.full_clean()
        lang.save()
        u1 = m.UnitType(
            label='foo',
        )
        u1.full_clean()
        u1.save()
        u2 = m.UnitType(
            label='bar',
        )
        u2.full_clean()
        u2.save()

    def test_duplicate_language_error(self):
        def aux():
            u = m.UnitType.objects.get(label='foo')
            lang = m.Language.objects.get(code='en')
            t1 = m.UnitTypeTranslation(
                unit_type=u,
                language=lang,
                localized_text='Foo',
            )
            t1.full_clean()
            t1.save()
            t2 = m.UnitTypeTranslation(
                unit_type=u,
                language=lang,
                localized_text='Foooo',
            )
            t2.full_clean()
            t2.save()

        self.assertRaises(dj_exc.ValidationError, aux)

    def test_empty_text_error(self):
        def aux():
            m.UnitTypeTranslation(
                unit_type=m.UnitType.objects.get(label='foo'),
                language=m.Language.objects.get(code='en'),
                localized_text='',
            ).full_clean()

        self.assertRaises(dj_exc.ValidationError, aux)

    def test_same_language_two_unit_types(self):
        lang = m.Language.objects.get(code='en')
        t1 = m.UnitTypeTranslation(
            unit_type=m.UnitType.objects.get(label='foo'),
            language=lang,
            localized_text='Foo',
        )
        t1.full_clean()
        t1.save()
        t2 = m.UnitTypeTranslation(
            unit_type=m.UnitType.objects.get(label='bar'),
            language=lang,
            localized_text='Foo',
        )
        t2.full_clean()
        t2.save()
        self.assertNotEqual(t1, t2)

    def test_deleted_if_unit_type_deleted(self):
        u = m.UnitType.objects.get(label='foo')
        t = m.UnitTypeTranslation(
            unit_type=u,
            language=m.Language.objects.get(code='en'),
            localized_text='Foo',
        )
        t.full_clean()
        t.save()
        self.assertTrue(m.UnitTypeTranslation.objects.filter(unit_type__id=u.id).exists())
        u.delete()
        self.assertFalse(m.UnitTypeTranslation.objects.filter(unit_type__id=u.id).exists())


# endregion
# region Enums

class EnumTypeTestCase(TestCase):
    def setUp(self):
        e = m.EnumType(
            label='enum',
        )
        e.full_clean()
        e.save()

    def test_label_not_unique_error(self):
        def aux():
            e1 = m.EnumType(
                label='foo',
            )
            e1.full_clean()
            e1.save()
            e2 = m.EnumType(
                label='foo',
            )
            e2.full_clean()
            e2.save()

        self.assertRaises(dj_exc.ValidationError, aux)

    def test_get_values(self):
        e = m.EnumType.objects.get(label='enum')
        v1 = m.EnumValue(
            label='bar',
            type=e,
        )
        v1.full_clean()
        v1.save()
        v2 = m.EnumValue(
            label='foo',
            type=e,
        )
        v2.full_clean()
        v2.save()
        self.assertEqual(e.get_values(), [v1, v2])

    def test_has_value(self):
        e = m.EnumType.objects.get(label='enum')
        v1 = m.EnumValue(
            label='bar',
            type=e,
        )
        v1.full_clean()
        v1.save()
        self.assertTrue(e.has_value(v1.label))

    def test_has_not_value(self):
        e = m.EnumType.objects.get(label='enum')
        v1 = m.EnumValue(
            label='bar',
            type=e,
        )
        v1.full_clean()
        v1.save()
        self.assertFalse(e.has_value('foo'))


class EnumTypeTranslationTestCase(TestCase):
    def setUp(self):
        dtf = m.DateTimeFormat(
            format='%d/%m/%y',
        )
        dtf.full_clean()
        dtf.save()
        lang = m.Language(
            code='en',
            name='English',
            writing_direction='ltr',
            available_for_ui=True,
            default_datetime_format=dtf,
        )
        lang.full_clean()
        lang.save()
        e1 = m.EnumType(
            label='enum1',
        )
        e1.full_clean()
        e1.save()
        e2 = m.EnumType(
            label='enum2',
        )
        e2.full_clean()
        e2.save()

    def test_duplicate_language_error(self):
        def aux():
            e = m.EnumType.objects.get(label='enum1')
            lang = m.Language.objects.get(code='en')
            t1 = m.EnumTypeTranslation(
                enum_type=e,
                language=lang,
                localized_text='Foo',
            )
            t1.full_clean()
            t1.save()
            t2 = m.EnumTypeTranslation(
                enum_type=e,
                language=lang,
                localized_text='Foooo',
            )
            t2.full_clean()
            t2.save()

        self.assertRaises(dj_exc.ValidationError, aux)

    def test_empty_text_error(self):
        def aux():
            m.EnumTypeTranslation(
                enum_type=m.EnumType.objects.get(label='enum1'),
                language=m.Language.objects.get(code='en'),
                localized_text='',
            ).full_clean()

        self.assertRaises(dj_exc.ValidationError, aux)

    def test_same_language_two_enum_types(self):
        lang = m.Language.objects.get(code='en')
        t1 = m.EnumTypeTranslation(
            enum_type=m.EnumType.objects.get(label='enum1'),
            language=lang,
            localized_text='Foo',
        )
        t1.full_clean()
        t1.save()
        t2 = m.EnumTypeTranslation(
            enum_type=m.EnumType.objects.get(label='enum2'),
            language=lang,
            localized_text='Foo',
        )
        t2.full_clean()
        t2.save()
        self.assertNotEqual(t1, t2)

    def test_deleted_if_enum_type_deleted(self):
        e = m.EnumType.objects.get(label='enum1')
        t = m.EnumTypeTranslation(
            enum_type=e,
            language=m.Language.objects.get(code='en'),
            localized_text='Foo',
        )
        t.full_clean()
        t.save()
        self.assertTrue(m.EnumTypeTranslation.objects.filter(enum_type__id=e.id).exists())
        e.delete()
        self.assertFalse(m.EnumTypeTranslation.objects.filter(enum_type__id=e.id).exists())


class EnumValueTestCase(TestCase):
    def setUp(self):
        e = m.EnumType(
            label='enum',
        )
        e.full_clean()
        e.save()
        v = m.EnumValue(
            label='foo',
            type=e,
        )
        v.full_clean()
        v.save()

    def test_duplicate_name_error(self):
        def aux():
            e = m.EnumType.objects.get(label='enum')
            v = m.EnumValue(
                label='foo',
                type=e,
            )
            v.full_clean()
            v.save()

        self.assertRaises(dj_exc.ValidationError, aux)

    def test_same_name_two_enum_types(self):
        e = m.EnumType(
            label='enum2',
        )
        e.full_clean()
        e.save()
        v = m.EnumValue(
            label='foo',
            type=e,
        )
        v.full_clean()
        v.save()

        e2 = m.EnumType.objects.get(label='enum')
        self.assertEqual(e2.get_values(), [m.EnumValue.objects.get(label='foo', type__id=e2.id)])
        self.assertEqual(e.get_values(), [v])

    def test_deleted_if_enum_type_deleted(self):
        m.EnumType.objects.get(label='enum').delete()
        self.assertFalse(m.EnumValue.objects.filter(label='foo').exists())


class EnumValueTranslationTestCase(TestCase):
    def setUp(self):
        dtf = m.DateTimeFormat(
            format='%d/%m/%y',
        )
        dtf.full_clean()
        dtf.save()
        lang = m.Language(
            code='en',
            name='English',
            writing_direction='ltr',
            available_for_ui=True,
            default_datetime_format=dtf,
        )
        lang.full_clean()
        lang.save()
        e = m.EnumType(
            label='enum',
        )
        e.full_clean()
        e.save()
        v1 = m.EnumValue(
            label='bar',
            type=e,
        )
        v1.full_clean()
        v1.save()
        v2 = m.EnumValue(
            label='foo',
            type=e,
        )
        v2.full_clean()
        v2.save()

    def test_duplicate_language_error(self):
        def aux():
            v = m.EnumValue.objects.get(label='foo')
            lang = m.Language.objects.get(code='en')
            t1 = m.EnumValueTranslation(
                enum_value=v,
                language=lang,
                localized_text='Foo',
            )
            t1.full_clean()
            t1.save()
            t2 = m.EnumValueTranslation(
                enum_value=v,
                language=lang,
                localized_text='Foooo',
            )
            t2.full_clean()
            t2.save()

        self.assertRaises(dj_exc.ValidationError, aux)

    def test_empty_text_error(self):
        def aux():
            m.EnumValueTranslation(
                enum_value=m.EnumValue.objects.get(label='foo'),
                language=m.Language.objects.get(code='en'),
                localized_text='',
            ).full_clean()

        self.assertRaises(dj_exc.ValidationError, aux)

    def test_same_language_two_enum_values(self):
        lang = m.Language.objects.get(code='en')
        t1 = m.EnumValueTranslation(
            enum_value=m.EnumValue.objects.get(label='foo'),
            language=lang,
            localized_text='Foo',
        )
        t1.full_clean()
        t1.save()
        t2 = m.EnumValueTranslation(
            enum_value=m.EnumValue.objects.get(label='bar'),
            language=lang,
            localized_text='Foo',
        )
        t2.full_clean()
        t2.save()
        self.assertNotEqual(t1, t2)

    def test_deleted_if_enum_value_deleted(self):
        v = m.EnumValue.objects.get(label='foo')
        t = m.EnumValueTranslation(
            enum_value=v,
            language=m.Language.objects.get(code='en'),
            localized_text='Foo',
        )
        t.full_clean()
        t.save()
        self.assertTrue(m.EnumValueTranslation.objects.filter(enum_value__id=v.id).exists())
        v.delete()
        self.assertFalse(m.EnumValueTranslation.objects.filter(enum_value__id=v.id).exists())

# endregion
