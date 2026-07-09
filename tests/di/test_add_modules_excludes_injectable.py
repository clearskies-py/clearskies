"""Regression tests: Di.add_modules() must not auto-register Injectable subclasses by name.

Injectable subclasses (clearskies.di.inject.*, and any third-party equivalents) only do anything
useful via the descriptor protocol (`__get__`), when used as a class attribute
(`foo = SomeInjectable()`) on an `InjectableProperties` class. They are not domain/application
classes meant to be built standalone and resolved by name.

Before this fix, `add_modules()` treated every discovered class the same way (aside from
`AdditionalConfigAutoImport`/`AdditionalMygrationsAutoImport`), including `Injectable` subclasses.
Since `add_classes()` derives a DI name from the class name (TitleCase -> snake_case), any
`Injectable` subclass whose name happened to match a `provide_<name>` method elsewhere in the same
module tree would silently shadow it: `build_from_name(name)` checks registered classes before
`AdditionalConfig`/`provide_<name>` methods, so callers received a bare, un-wired instance of the
`Injectable` subclass (built via a plain constructor call, never through `__get__`) instead of
whatever the `provide_<name>` method was supposed to build.

This is exactly what happened in clear-skies-aws: `clearskies_aws.di.inject.boto3.Boto3` collided
with the DI name "boto3", breaking `BaseAwsClient.boto3 = ByStandardLib("boto3")` with
`AttributeError: 'Boto3' object has no attribute 'client'`.
"""

import unittest

from clearskies.di import AdditionalConfigAutoImport, Di
from clearskies.di.injectable import Injectable


class AdditionalConfigAutoImportExample(AdditionalConfigAutoImport):
    def provide_boto3_like_thing(self) -> str:
        return "the real thing"


class AddModulesExcludesInjectableTest(unittest.TestCase):
    def test_injectable_subclass_is_not_registered_as_a_class(self):
        import tests.di.injectable_module as injectable_module

        di = Di()
        di.add_modules([injectable_module])

        self.assertNotIn("boto3_like_thing", di._classes)

    def test_provide_method_is_not_shadowed_by_a_same_named_injectable(self):
        import tests.di.injectable_module as injectable_module

        di = Di()
        di.add_modules([injectable_module])
        di.add_additional_configs([AdditionalConfigAutoImportExample()])

        result = di.build_from_name("boto3_like_thing")

        self.assertEqual("the real thing", result)

    def test_injectable_subclass_still_works_normally_as_a_descriptor(self):
        """The exclusion must not break legitimate Injectable usage as a class attribute."""
        import tests.di.injectable_module as injectable_module
        from clearskies.di.injectable_properties import InjectableProperties

        class Consumer(InjectableProperties):
            boto3_like_thing = injectable_module.Boto3LikeThing()

        di = Di()
        di.add_modules([injectable_module])
        di.add_additional_configs([AdditionalConfigAutoImportExample()])

        consumer = di.build_class(Consumer)
        self.assertEqual("the real thing", consumer.boto3_like_thing)

    def test_bare_injectable_class_is_excluded_too(self):
        """Sanity check directly against the abstract base, not just a fixture subclass."""

        class SomeInjectable(Injectable):
            def __get__(self, instance, parent):
                if instance is None:
                    return self
                return "unused"

        import types

        module = types.ModuleType("synthetic_injectable_module")
        module.__file__ = __file__
        module.__dict__["SomeInjectable"] = SomeInjectable

        di = Di()
        di.add_modules([module])

        self.assertNotIn("some_injectable", di._classes)


if __name__ == "__main__":
    unittest.main()
