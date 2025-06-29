import clearskies

from app.build import build

app = clearskies.EndpointGroup([
    clearskies.endpoints.Callable(build),
])
