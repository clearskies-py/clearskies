import datetime
import os
import unittest

import requests

import clearskies.configs
import clearskies.decorators
from clearskies.di import AdditionalConfig, Di, InjectableProperties, inject
from clearskies.exceptions import MissingDependency
from tests.di.module_scoped_shared import (
    ConfigurableBackend,
    DefaultBackend,
    GlobalReplacementDependency,
    ModuleScopedBackend,
    SharedDependency,
    SharedDependencySubclass,
)


class SomeClass:
    def __init__(self, my_value: int):
        self.my_value = my_value


class MyClass:
    def __init__(self, some_specific_value: int, some_class: SomeClass):
        self.final_value = some_specific_value * some_class.my_value


class VeryNeedy:
    def __init__(self, my_class, some_other_value: str):
        self.my_class = my_class
        self.some_other_value = some_other_value


class MyOtherProvider(AdditionalConfig):
    def provide_some_specific_value(self):
        return 10


class MyProvider(AdditionalConfig):
    def provide_some_specific_value(self):
        return 5

    def can_build_class(self, class_to_check: type) -> bool:
        return class_to_check == SomeClass

    def build_class(self, class_to_provide: type, argument_name: str, di, context: str = ""):
        if class_to_provide == SomeClass:
            return SomeClass(5)
        raise ValueError(f"I was asked to build a class I didn't expect '{class_to_provide.__name__}'")


def my_function(this_uses_type_hinting_exclusively: VeryNeedy):
    return f"Jane owns {this_uses_type_hinting_exclusively.my_class.final_value} {this_uses_type_hinting_exclusively.some_other_value}s"


class DiTest(unittest.TestCase):
    def test_di_class_examples(self):
        di = Di(
            classes=[MyClass, VeryNeedy, SomeClass],
            additional_configs=[MyProvider(), MyOtherProvider()],
            bindings={
                "some_other_value": "dog",
            },
        )

        assert di.call_function(my_function) == "Jane owns 50 dogs"

    def test_add_classes_example(self):
        class MyClass:
            name = "Simple Demo"

        def my_function(my_class):
            return my_class.name

        di = Di(classes=[MyClass])
        assert "Simple Demo" == di.call_function(my_function)

        di = Di()
        di.add_classes(MyClass)
        assert "Simple Demo" == di.call_function(my_function)

    def test_add_modules_example(self):
        from . import my_module

        def my_function(my_class):
            return my_class.count

        di = Di(modules=my_module)
        assert di.call_function(my_function) == 5

        di = Di()
        di.add_modules([my_module])
        assert di.call_function(my_function) == 5

    def test_add_additional_config(self):
        class MyConfig(AdditionalConfig):
            def provide_some_value(self):
                return 2

            def provide_another_value(self, some_value):
                return some_value * 2

        def my_function(another_value):
            return another_value

        di = Di()
        di.add_additional_configs([MyConfig()])
        assert di.call_function(my_function) == 4

        di = Di(additional_configs=[MyConfig()])
        assert di.call_function(my_function) == 4

    def test_add_binding(self):
        def my_function(my_name):
            return my_name

        di = Di()
        di.add_binding("my_name", 12345)
        assert di.call_function(my_function) == 12345

        di = Di(bindings={"my_name": 12345})
        assert di.call_function(my_function) == 12345

    def test_add_class_override(self):
        class TypeHintedClass:
            my_value = 5

        class ReplacementClass:
            my_value = 10

        di = Di()
        di.add_classes(TypeHintedClass)
        di.add_class_override(TypeHintedClass, ReplacementClass)

        def my_function(some_value: TypeHintedClass):
            return some_value.my_value

        assert di.call_function(my_function) == 10

        di = Di(classes=[TypeHintedClass], class_overrides={TypeHintedClass: ReplacementClass})
        assert di.call_function(my_function) == 10

    def test_module_scoped_class_override_applies_to_own_module(self):
        import tests.di.module_scoped_a as module_scoped_a
        import tests.di.module_scoped_b as module_scoped_b

        di = Di(classes=[SharedDependency], modules=[module_scoped_a, module_scoped_b])

        from tests.di.module_scoped_a import ModuleAClass
        from tests.di.module_scoped_b import ModuleBClass

        module_a_class = di.build_class(ModuleAClass)
        module_b_class = di.build_class(ModuleBClass)

        assert isinstance(module_a_class.shared_dependency, SharedDependencySubclass)
        assert module_a_class.module_value == "module-a"
        assert isinstance(module_a_class.backend, ModuleScopedBackend)
        assert isinstance(module_b_class.shared_dependency, SharedDependency)
        assert not isinstance(module_b_class.shared_dependency, SharedDependencySubclass)
        assert module_b_class.module_value == "module-b-default"
        assert isinstance(module_b_class.backend, DefaultBackend)

    def test_module_scoped_class_override_does_not_leak_to_other_modules(self):
        import tests.di.module_scoped_a as module_scoped_a
        import tests.di.module_scoped_b as module_scoped_b

        di = Di(classes=[SharedDependency], modules=[module_scoped_a, module_scoped_b])

        from tests.di.module_scoped_b import ModuleBClass

        module_b_class = di.build_class(ModuleBClass)
        assert isinstance(module_b_class.shared_dependency, SharedDependency)
        assert module_b_class.shared_dependency.source == "shared"

    def test_global_class_override_beats_module_scoped_class_override(self):
        import tests.di.module_scoped_a as module_scoped_a

        di = Di(
            classes=[SharedDependency],
            modules=[module_scoped_a],
            class_overrides={SharedDependency: GlobalReplacementDependency},
        )

        from tests.di.module_scoped_a import ModuleAClass

        module_a_class = di.build_class(ModuleAClass)
        assert isinstance(module_a_class.shared_dependency, GlobalReplacementDependency)

    def test_module_scoped_class_override_does_not_apply_to_subclasses(self):
        import tests.di.module_scoped_a as module_scoped_a

        class Consumer:
            def __init__(self, shared_dependency_subclass: SharedDependencySubclass):
                self.shared_dependency_subclass = shared_dependency_subclass

        di = Di(classes=[SharedDependencySubclass, Consumer], modules=[module_scoped_a])

        consumer = di.build_class(Consumer)
        assert isinstance(consumer.shared_dependency_subclass, SharedDependencySubclass)

    def test_module_scoped_class_override_ignores_empty_context(self):
        import tests.di.module_scoped_a as module_scoped_a

        di = Di(classes=[SharedDependency], modules=[module_scoped_a])

        value = di.build_class_from_type_hint("shared_dependency", SharedDependency, context="")
        assert isinstance(value, SharedDependency)

    def test_module_scoped_binding_applies_to_own_module(self):
        import tests.di.module_scoped_a as module_scoped_a
        import tests.di.module_scoped_b as module_scoped_b

        di = Di(classes=[SharedDependency], modules=[module_scoped_a, module_scoped_b])

        from tests.di.module_scoped_a import ModuleAClass
        from tests.di.module_scoped_b import ModuleBClass

        module_a_class = di.build_class(ModuleAClass)
        module_b_class = di.build_class(ModuleBClass)

        assert module_a_class.module_value == "module-a"
        assert module_b_class.module_value == "module-b-default"

    def test_global_binding_beats_module_scoped_binding(self):
        import tests.di.module_scoped_a as module_scoped_a

        di = Di(classes=[SharedDependency], modules=[module_scoped_a], bindings={"module_value": "global"})

        from tests.di.module_scoped_a import ModuleAClass

        module_a_class = di.build_class(ModuleAClass)
        assert module_a_class.module_value == "global"

    def test_module_scoped_binding_ignores_empty_context(self):
        import tests.di.module_scoped_a as module_scoped_a

        di = Di(classes=[SharedDependency], modules=[module_scoped_a])

        with self.assertRaises(MissingDependency):
            di.build_from_name("module_value", context="")

    def test_global_config_override_patches_configurable_instance(self):
        import tests.di.module_scoped_a as module_scoped_a

        di = Di(
            classes=[SharedDependency],
            modules=[module_scoped_a],
            config_overrides={ConfigurableBackend: {"base_url": "https://global-override.example.com"}},
        )

        from tests.di.module_scoped_a import ModuleAClass

        module_a_class = di.build_class(ModuleAClass)
        assert module_a_class.configurable_backend.base_url == "https://global-override.example.com"

    def test_module_scoped_config_override_patches_configurable_instance(self):
        import tests.di.module_scoped_a as module_scoped_a
        import tests.di.module_scoped_b as module_scoped_b

        di = Di(classes=[SharedDependency], modules=[module_scoped_a, module_scoped_b])

        from tests.di.module_scoped_a import ModuleAClass
        from tests.di.module_scoped_b import ModuleBClass

        module_a_class = di.build_class(ModuleAClass)
        module_b_class = di.build_class(ModuleBClass)

        # module A has config override — patched
        assert module_a_class.configurable_backend.base_url == "https://module-a.example.com"
        assert module_a_class.configurable_backend.api_version == "v2"
        # module B has no config override — default values
        assert module_b_class.configurable_backend.base_url == "https://default.example.com"
        assert module_b_class.configurable_backend.api_version == "v1"

    def test_global_config_override_beats_module_scoped_config_override(self):
        import tests.di.module_scoped_a as module_scoped_a

        di = Di(
            classes=[SharedDependency],
            modules=[module_scoped_a],
            config_overrides={ConfigurableBackend: {"base_url": "https://global.example.com"}},
        )

        from tests.di.module_scoped_a import ModuleAClass

        module_a_class = di.build_class(ModuleAClass)
        assert module_a_class.configurable_backend.base_url == "https://global.example.com"

    def test_config_override_does_not_affect_non_configurable_attributes(self):
        import tests.di.module_scoped_a as module_scoped_a

        di = Di(
            classes=[SharedDependency],
            modules=[module_scoped_a],
            config_overrides={DefaultBackend: {"source": "patched"}},
        )

        from tests.di.module_scoped_a import ModuleAClass

        # DefaultBackend is not Configurable — should be left as-is (or replaced by module class override)
        module_a_class = di.build_class(ModuleAClass)
        assert isinstance(module_a_class.backend, ModuleScopedBackend)

    def test_global_class_override_beats_module_scoped_override_for_injectable_properties(self):
        import tests.di.module_scoped_a as module_scoped_a

        class GlobalBackend(DefaultBackend):
            source = "global-backend"

        di = Di(
            classes=[SharedDependency],
            modules=[module_scoped_a],
            class_overrides={DefaultBackend: GlobalBackend},
        )

        from tests.di.module_scoped_a import ModuleAClass

        module_a_class = di.build_class(ModuleAClass)
        assert isinstance(module_a_class.backend, GlobalBackend)

    def test_now(self):
        di = Di()
        now = datetime.datetime.now()
        also_now = di.build("now")
        assert now.year == also_now.year
        assert now.month == also_now.month
        assert now.day == also_now.day
        assert also_now.tzinfo == None

        di.set_now(now)
        assert now == di.build("now")
        assert now != also_now

    def test_utcnow(self):
        di = Di()
        utcnow = datetime.datetime.now(datetime.timezone.utc)
        also_utcnow = di.build("utcnow")
        assert utcnow.year == also_utcnow.year
        assert utcnow.month == also_utcnow.month
        assert utcnow.day == also_utcnow.day
        assert also_utcnow.tzinfo == datetime.timezone.utc

        di.set_utcnow(utcnow)
        assert utcnow == di.build("utcnow")
        assert utcnow != also_utcnow

    def test_requests(self):
        di = Di()
        assert isinstance(di.build("requests"), requests.Session)
        assert di.build("requests", cache=True) == di.build("requests", cache=True)
        assert di.build("requests", cache=True) != di.build(requests.Session, cache=True)
        assert di.build(requests.Session, cache=True) == di.build(requests.Session, cache=True)

    def test_inject(self):
        class MySubDep(InjectableProperties):
            requests = inject.Requests()
            value = inject.ByName("asdfer")

        class MyClass(InjectableProperties):
            di = inject.Di()
            now = inject.Now()
            my_sub_dep = inject.ByClass(MySubDep)

        di = Di(bindings={"asdfer": "hey"})
        now = datetime.datetime.now()
        di.set_now(now)
        my_class = di.build_class(MyClass)
        assert now == my_class.now
        assert di == my_class.di
        assert isinstance(my_class.my_sub_dep, MySubDep)
        assert isinstance(my_class.my_sub_dep.requests, requests.Session)
        assert my_class.my_sub_dep.value == "hey"

    def test_injectable_example(self):
        class MyOtherThing(InjectableProperties):
            now = inject.Now()

        class ReusableClass(clearskies.Configurable, InjectableProperties):
            my_int = clearskies.configs.Integer(required=True)
            some_number = inject.ByName("some_number")
            my_other_thing = inject.ByClass(MyOtherThing)

            @clearskies.decorators.parameters_to_properties
            def __init__(self, my_int: int):
                self.finalize_and_validate_configuration()

            def my_value(self) -> int:
                return self.my_int * self.some_number

        class MyClass(InjectableProperties):
            reusable = ReusableClass(5)

        class MyOtherClass(InjectableProperties):
            reusable = ReusableClass(10)

        di = Di(
            bindings={
                "some_number": 10,
            }
        )

        my_class = di.build(MyClass)
        assert my_class.reusable.my_value() == 50

        my_other_class = di.build(MyOtherClass)
        assert my_other_class.reusable.my_value() == 100

        assert isinstance(my_class.reusable.my_other_thing.now, datetime.datetime)

    def test_build_standard_lib_simple_module(self):
        """Test that build_standard_lib can import simple modules like 'os' and 'sys'."""
        di = Di()

        # Test importing 'os' module
        os_module = di.build_standard_lib("os")
        assert os_module is not None
        assert hasattr(os_module, "environ")
        assert hasattr(os_module, "path")

        # Test importing 'sys' module
        sys_module = di.build_standard_lib("sys")
        assert sys_module is not None
        assert hasattr(sys_module, "version")

    def test_build_standard_lib_dotted_attribute(self):
        """Test that build_standard_lib can handle dotted names like 'os.environ'."""
        di = Di()

        # Test getting os.environ
        environ = di.build_standard_lib("os.environ")
        assert environ is not None
        assert environ is os.environ
        assert isinstance(environ, os._Environ)

        # Test getting os.path
        path_module = di.build_standard_lib("os.path")
        assert path_module is not None
        assert hasattr(path_module, "join")
        assert hasattr(path_module, "exists")

    def test_build_standard_lib_imports_dotted_module_name(self):
        """Test that build_standard_lib imports dotted module names before attribute traversal."""
        di = Di()

        # Importable as a submodule, but not as an attribute on json
        result = di.build_standard_lib("json.tool")
        assert result is not None
        assert result.__name__ == "json.tool"

    def test_build_standard_lib_caches_result(self):
        """Test that build_standard_lib caches the result when cache=True."""
        di = Di()

        # First call should import and cache
        environ1 = di.build_standard_lib("os.environ", cache=True)
        # Second call should return cached value
        environ2 = di.build_standard_lib("os.environ", cache=True)

        assert environ1 is environ2
        assert environ1 is os.environ

    def test_build_standard_lib_raises_for_invalid_module(self):
        """Test that build_standard_lib raises MissingDependency for invalid modules."""
        di = Di()

        with self.assertRaises(MissingDependency):
            di.build_standard_lib("nonexistent_module_xyz")

    def test_build_standard_lib_raises_for_invalid_attribute(self):
        """Test that build_standard_lib raises MissingDependency for invalid attributes."""
        di = Di()

        with self.assertRaises(MissingDependency):
            di.build_standard_lib("os.nonexistent_attribute_xyz")

    def test_build_standard_lib_missing_dotted_name_raises(self):
        """Test that dotted names that are neither modules nor attributes raise MissingDependency."""
        di = Di()

        with self.assertRaises(MissingDependency):
            di.build_standard_lib("json.definitely_not_real")

    def test_build_standard_lib_deep_dotted_path(self):
        """Test that build_standard_lib can handle deeper dotted paths."""
        di = Di()

        # Test getting os.path.join (a function)
        join_func = di.build_standard_lib("os.path.join")
        assert join_func is not None
        assert callable(join_func)
        assert join_func("a", "b") == os.path.join("a", "b")

    def test_inject_by_standard_lib_with_dotted_name(self):
        """Test that ByStandardLib injectable works with dotted names like 'os.environ'."""

        class MyClassWithEnv(InjectableProperties):
            os_environ = inject.ByStandardLib("os.environ")

        di = Di()
        my_instance = di.build_class(MyClassWithEnv)

        assert my_instance.os_environ is os.environ
        assert isinstance(my_instance.os_environ, os._Environ)

    def test_inject_by_standard_lib_with_simple_module(self):
        """Test that ByStandardLib injectable works with simple module names."""

        class MyClassWithOs(InjectableProperties):
            os_module = inject.ByStandardLib("os")

        di = Di()
        my_instance = di.build_class(MyClassWithOs)

        assert my_instance.os_module is not None
        assert hasattr(my_instance.os_module, "environ")
        assert hasattr(my_instance.os_module, "path")
