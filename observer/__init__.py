import asyncio


# Borrowed from aioreactive
class Observable:
    def __init__(self):
        self._push = asyncio.Future()
        self._pull = asyncio.Future()
        self._awaiters = []
        self._busy = False

    async def send(self, value):
        await self._serialize_access()
        self._push.set_result(value)
        await self._wait_for_pull()

    async def set_exception(self, err):
        await self._serialize_access()
        self._push.set_exception(err)
        await self._wait_for_pull()

    async def stop(self):
        await self._serialize_access()
        self._push.set_exception(StopAsyncIteration)
        await self._wait_for_pull()

    async def _wait_for_pull(self):
        await self._pull
        self._pull = asyncio.Future()
        self._busy = False

    async def _serialize_access(self):
        while self._busy:
            future = asyncio.Future()
            self._awaiters.append(future)
            await future
            self._awaiters.remove(future)

        self._busy = True

    async def wait_for_push(self):
        value = await self._push
        self._push = asyncio.Future()
        self._pull.set_result(True)

        for awaiter in self._awaiters[:1]:
            awaiter.set_result(True)
        return value

    async def __aiter__(self):
        return self

    async def __anext__(self):
        return await self.wait_for_push()


class Subject:
    def __init__(self, *, loop=None):
        self._push = asyncio.Future()
        self._observables = []

    def _filter_observables(self):
        for sub in self._observables:
            if sub._push.cancelled():
                continue
            yield sub

    async def send(self, msg):
        self._observables = list(self._filter_observables())
        for sub in self._observables:
            await sub.send(msg)

    async def stop(self):
        self._observables = list(self._filter_observables())
        self._push.set_result(None)
        for sub in self._observables:
            await sub.stop()

    async def set_exception(self, exc):
        self._observables = list(self._filter_observables())
        self._push.set_result(exc)
        for sub in self._observables:
            await sub.set_exception(exc)

    def __await__(self):
        return self._push.__await__()

    async def __aiter__(self):
        obv = Observable()
        self._observables.append(obv)
        return obv


def consume(generator):
    observer = Subject()

    async def closure():
        try:
            async for msg in generator:
                await observer.send(msg)
        except Exception as exc:
            await observer.set_exception(exc)
        else:
            await observer.stop()

    asyncio.ensure_future(closure())
    return observer


def subscribe(function):
    subscription = Observable()

    async def closure():
        try:
            await function(subscription)
        except Exception as exc:
            await subscription.set_exception(exc)
        else:
            await subscription.stop()

    asyncio.ensure_future(closure())
    return subscription
