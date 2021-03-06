import time
import hashlib

from django.core.cache import caches

from pretix.base.models import Event


class EventRelatedCache:
    """
    This object behaves exactly like the cache implementations by Django
    but with one important difference: It stores all keys related to a
    certain event, so you pass an event when creating this object and if
    you store data in this cache, it is only stored for this event. The
    main purpose of this is to be able to flush all cached data related
    to this event at once.

    The EventRelatedCache instance itself is stateless, all state is
    stored in the cache backend, so you can instantiate this class as many
    times as you want.
    """

    def __init__(self, event: Event, cache: str='default'):
        assert isinstance(event, Event)
        self.cache = caches[cache]
        self.event = event
        self.prefixkey = 'event:%s' % self.event.pk

    def _prefix_key(self, original_key: str) -> str:
        # Race conditions can happen here, but should be very very rare.
        # We could only handle this by going _really_ lowlevel using
        # memcached's `add` keyword instead of `set`.
        # See also:
        # https://code.google.com/p/memcached/wiki/NewProgrammingTricks#Namespacing
        prefix = self.cache.get(self.prefixkey)
        if prefix is None:
            prefix = int(time.time())
            self.cache.set(self.prefixkey, prefix)
        key = 'event:%s:%d:%s' % (self.event.pk, prefix, original_key)
        if len(key) > 200:  # Hash long keys, as memcached has a length limit
            # TODO: Use a more efficient, non-cryptographic hash algorithm
            key = hashlib.sha256(key.encode("UTF-8")).hexdigest()
        return key

    @staticmethod
    def _strip_prefix(key: str) -> str:
        return key.split(":", 3)[-1] if 'event:' in key else key

    def clear(self):
        try:
            prefix = self.cache.incr(self.prefixkey, 1)
        except ValueError:
            prefix = int(time.time())
            self.cache.set(self.prefixkey, prefix)

    def set(self, key: str, value: str, timeout: int=3600):
        return self.cache.set(self._prefix_key(key), value, timeout)

    def get(self, key: str) -> str:
        return self.cache.get(self._prefix_key(key))

    def get_many(self, keys: "list[str]") -> "dict[str, str]":
        values = self.cache.get_many([self._prefix_key(key) for key in keys])
        newvalues = {}
        for k, v in values.items():
            newvalues[self._strip_prefix(k)] = v
        return newvalues

    def set_many(self, values: "dict[str, str]", timeout=3600):
        newvalues = {}
        for k, v in values.items():
            newvalues[self._prefix_key(k)] = v
        return self.cache.set_many(newvalues, timeout)

    def delete(self, key: str):  # NOQA
        return self.cache.delete(self._prefix_key(key))

    def delete_many(self, keys: "list[str]"):  # NOQA
        return self.cache.delete_many([self._prefix_key(key) for key in keys])

    def incr(self, key: str, by: int=1):  # NOQA
        return self.cache.incr(self._prefix_key(key), by)

    def decr(self, key: str, by: int=1):  # NOQA
        return self.cache.decr(self._prefix_key(key), by)

    def close(self):  # NOQA
        pass
