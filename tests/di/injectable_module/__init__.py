"""Fixture module for tests/di/test_add_modules_excludes_injectable.py.

Contains an `Injectable` subclass whose name would, if auto-registered by name via
`Di.add_modules()`, collide with `provide_boto3_like_thing()` on `AdditionalConfigAutoImportExample`
in the test file - mirroring the real-world clear-skies-aws bug this fixture exists to guard against
(`clearskies_aws.di.inject.boto3.Boto3` colliding with the DI name "boto3").
"""

from clearskies.di.injectable import Injectable


class Boto3LikeThing(Injectable):
    def __init__(self, cache: bool = True):
        self.cache = cache

    def __get__(self, instance, parent):
        if instance is None:
            return self
        return self._di.build_from_name("boto3_like_thing", cache=self.cache)


__all__ = ["Boto3LikeThing"]
