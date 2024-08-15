# parametric

`parametric` is a Python library designed for managing and validating immutable parameters. `parametric` focuses exclusively on immutability, ensuring that all parameters are immutable objects. It also allows for empty fields before freezing, making it a robust choice for configuration management in applications where parameter mutability is a concern.

## Key Features

- **Immutable Parameters:** `parametric` enforces immutability by restricting parameters to immutable types such as `int`, `float`, `str`, `tuple`, etc.
- **Flexible Initialization:** You can initialize parameters with empty fields, which must be filled before the object is frozen.
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
    data_dirs: tuple[str, ...]
    num_classes_without_bg: int | None = None
    dataset_name: str | None = None
    image_shape: tuple[int, int] = (640, 640)
    nn_encoder_name: str = "efficientnet-b0"
    nn_default_encoder_weights: str = "imagenet"
    num_epochs: int = 1000
    train_batch_size: int = 12
    val_batch_size: int = 36

params = MyParams()
params.data_dirs = ("path/to/data",)
params.num_classes_without_bg = 3
params.freeze()  # Freeze the parameters, making them immutable
```

## Override Mechanisms

`parametric` provides multiple ways to override parameters:

### 1. Override from CLI

```python
import sys
from parametric import BaseParams

class MyParams(BaseParams):
    num_epochs: int = 1000

params = MyParams()
params.override_from_cli()
params.freeze()
```

Run the script with:

```bash
python script.py --num_epochs 500
```

### 2. Override from Environment Variables

```python
import os
from parametric import BaseParams

class MyParams(BaseParams):
    val_batch_size: int = 36

params = MyParams()
params.override_from_envs(env_prefix="_param_")
params.freeze()
```

Set the environment variable:

```bash
export _param_val_batch_size=32
```

### 3. Override from YAML File

```python
from parametric import BaseParams

class MyParams(BaseParams):
    train_batch_size: int = 12

params = MyParams()
params.override_from_yaml("config.yaml")
params.freeze()
```

Example `config.yaml`:

```yaml
train_batch_size: 8
```

### 4. Override from Dictionary

```python
from parametric import BaseParams

class MyParams(BaseParams):
    num_epochs: int = 1000

params = MyParams()
params.override_from_dict({"num_epochs": 500})
params.freeze()
```

## Comparison with Pydantic

The main difference between `parametric` and `pydantic` lies in their design philosophy:

- **Immutability:** `parametric` restricts all parameters to immutable types, making it suitable for use cases where configuration parameters should not change after initialization.
- **Flexibility with Empty Fields:** `parametric` allows empty fields during initialization, which must be set before freezing, offering flexibility during the setup phase.

## Contributing

Contributions are welcome! Please submit issues or pull requests on the GitHub repository.
