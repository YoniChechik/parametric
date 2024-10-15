# `parametric`

`parametric` is a Python library designed for managing and validating immutable parameters. It is built around `pydantic` and enhances it by focusing on immutability and custom configurations, making it a robust choice for configuration management in applications and especially data-science pipelines.

## Key Features

- **Immutable Parameters:** `parametric` enforces immutability by restricting parameters to immutable types such as `int`, `float`, `str`,`bool`,`bytes`,`tuple`,`None`,`pathlib.Path`,`Enum`,`Literal`, and `Union`s of those.
- **Freeze Mechanism:** `parametric` introduces a powerful freeze mechanism that allows fields to remain unset or mutable until explicitly frozen, at which point all fields are locked and cannot be modified.
- **Override Mechanisms:** Supports overriding parameters via CLI arguments, environment variables, YAML files, and dictionaries.
- **Serialization:** Parameters can be easily saved and loaded using YAML.

## Installation

You can install `parametric` via pip:

```bash
pip install parametric
```

## Getting Started

Here's a basic example to illustrate how to use `parametric`:

```python
from parametric import BaseParams

class MyParams(BaseParams):
    nn_encoder_name: str = "efficientnet-b0"
    nn_default_encoder_weights: str = "imagenet"
    image_shape: tuple[int, int] = (640, 640)
    num_epochs: int = 1000
    train_batch_size: int = 12
    val_batch_size: int | None = None

params = MyParams()
params.image_shape = (1024, 1024)
params.freeze()  # Freeze the parameters, making them immutable
```


## Override Mechanisms

`parametric` provides multiple ways to override parameters. Below are examples of how you can override parameters using different methods.

### 1. Override from CLI

You can override parameters by passing them as command-line arguments when running the script.

Run the script with:
```bash
python script.py --num_epochs 500
```

This example shows how to override `num_epochs` using CLI arguments:

```python
from parametric import BaseParams

class MyParams(BaseParams):
    num_epochs: int = 1000

params = MyParams()
params.override_from_cli()
params.freeze()

# NOTE: params.model_dump() is a function of pydantic.BaseModel we inherit from
print(params.model_dump())  # {'num_epochs': 500} 
```

### 2. Override from Environment Variables

You can override parameters by setting environment variables with a specified prefix before running the script.

Run the script with:
```bash
export _param_val_batch_size=32 && python script.py
```

This example shows how to override `val_batch_size` using environment variables:

```python
from parametric import BaseParams

class MyParams(BaseParams):
    val_batch_size: int = 36

params = MyParams()
params.override_from_envs(env_prefix="_param_")
params.freeze()

print(params.model_dump())  # {'val_batch_size': 32}
```

### 3. Override from YAML File

You can override parameters by loading values from a YAML configuration file.

Example `config.yaml`:

```yaml
train_batch_size: 8
```

This example shows how to override `train_batch_size` using values from `config.yaml`:

```python
from parametric import BaseParams

class MyParams(BaseParams):
    train_batch_size: int = 12

params = MyParams()
params.override_from_yaml("config.yaml")
params.freeze()

print(params.model_dump())  # {'train_batch_size': 8}
```

### 4. Override from Dictionary

You can override parameters by passing a dictionary directly into the model.

```python
from parametric import BaseParams

class MyParams(BaseParams):
    num_epochs: int = 1000

params = MyParams()
params.override_from_dict({"num_epochs": 500})
params.freeze()

print(params.model_dump())  # {'num_epochs': 500}
```

## Opinionated Usage

This is how we like to use `parametric` in our pipeline:
- We define a global params object in a dedicated module (e.g., `params.py`) to be shared across different modules in the pipeline.
- After overrides and changes are applied (in the start of the pipe is the best), the parameters are **frozen** to prevent accidental mutation. Because all params are immutable, no-one will change them accidentally.
- During development, we use a **git-ignored** YAML file (e.g., `params.yaml`) for configuration, allowing for easy debugging and experimentation without polluting the repository.

Let's see:

**`params.py`** (module to define the parameters and expose `params`):

```python
from pathlib import Path  # NOTE: every time a developer switches from str/os.path to pathlib.Path, an angel gets his wings!

from parametric import BaseParams


class MyParams(BaseParams):
    data_dirs: tuple[Path, ...]
    image_shape: tuple[int, int] = (640, 640)
    nn_encoder_name: str = "efficientnet-b0"
    nn_default_encoder_weights: str = "imagenet"
    num_epochs: int = 1000
    train_batch_size: int = 12
    val_batch_size: int = 36

params = MyParams()
```

**`main.py`**:

```python
from params import params
from module_a import run_pipeline


def main():

    params.override_from_yaml("params.yaml")

    # Optionally override via CLI
    params.override_from_cli()

    # Freeze the parameters to make them immutable
    params.freeze()

    # Proceed with the rest of the pipeline
    run_pipeline()


if __name__ == "__main__":
    main()
```

**`module_a.py`**:

```python
from params import params  # This can be imported in many more files as needed


def run_pipeline(): 
    # do stuff with params... e.g.:
    val_loader = dataloader(params.val_batch_size)
```

**`params.yaml`**:

This file is git-ignored (again, **just a suggestion**), all params here are example for debug senerio that overrides the defaults

```yaml
data_dirs:
  - "/path/to/data"
train_batch_size: 16
val_batch_size: 32
```

## Contributing

Contributions are welcome! Please submit issues or pull requests on the GitHub repository.

