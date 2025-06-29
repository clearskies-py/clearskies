import json
import pathlib
import sys

# this ensures that we will use the version of clearskies currently checked out.
my_path = pathlib.Path(__file__)
sys.path.append(str(my_path.parents[2] / 'src'))

import clearskies
import app

config_file = open("config.json", "r")
config = json.loads(config_file.read())
config_file.close()

project_root = str(my_path.parents[1])

cli = clearskies.contexts.Cli(
    app.app,
    modules=[app.models, app.backends],
    bindings={
        "config": config,
        "project_root": project_root,
    },
)
cli()
