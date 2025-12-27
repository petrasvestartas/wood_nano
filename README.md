wood_nano
=========



|      CI              | status |
|----------------------|--------|
| pip builds           | [![Pip Action Status][actions-pip-badge]][actions-pip-link] |
| wheels               | [![Wheel Action Status][actions-wheels-badge]][actions-wheels-link] |

[actions-pip-link]:        https://github.com/wjakob/nanobind_example/actions?query=workflow%3APip
[actions-pip-badge]:       https://github.com/wjakob/nanobind_example/workflows/Pip/badge.svg
[actions-wheels-link]:     https://github.com/wjakob/nanobind_example/actions?query=workflow%3AWheels
[actions-wheels-badge]:    https://github.com/wjakob/nanobind_example/workflows/Wheels/badge.svg


This repository contains a tiny project showing how to create C++ bindings
using [nanobind](https://github.com/wjakob/nanobind) and
[scikit-build-core](https://scikit-build-core.readthedocs.io/en/latest/index.html). It
was derived from the corresponding _pybind11_ [example
project](https://github.com/pybind/scikit_build_example/) developed by
[@henryiii](https://github.com/henryiii).

Installation
------------

1. Clone this repository
2. Run `pip install ./wood_nano`

CI Examples
-----------

The `.github/workflows` directory contains two continuous integration workflows
for GitHub Actions. The first one (`pip`) runs automatically after each commit
and ensures that packages can be built successfully and that tests pass.

The `wheels` workflow uses
[cibuildwheel](https://cibuildwheel.readthedocs.io/en/stable/) to automatically
produce binary wheels for a large variety of platforms. If a `pypi_password`
token is provided using GitHub Action's _secrets_ feature, this workflow can
even automatically upload packages on PyPI.


Customization
=============

Repository wood_nano has submodule wood in src directly.
For new clones incase there is nothing in the src/wood folder do the following:

```bash
 git submodule update --init --recursive
```

Conda
-----

```bash
conda config --add channels conda-forge
conda create -n wood python==3.8.16 pypy=7.3.11

```

Rhino ScriptEditor
------------------

```bash
C:/Users/petras/.rhinocode/py39-rh8/python.exe -m pip install . 
```

```python
import os
import os.path as op
import sys
import ctypes

CONDA_ENV = r'C:\Users\petras\.conda\envs\wood'
COMPAS_WOOD_PATH = r'C:\brg\2_code\wood_nano\build\pp38-pypy38_pp73-win_amd64\Release'
sys.path.append(op.join(CONDA_ENV, r"Lib\site-packages"))
sys.path.append(COMPAS_WOOD_PATH)
os.add_dll_directory(op.join(CONDA_ENV, r'Library\bin'))
os.add_dll_directory(COMPAS_WOOD_PATH)

import nanobind_example
print(nanobind_example.add(1, 2))

```

Wood submodule and download dependecies
---------------------------------------

```bash
cd ~/brg/2_code/wood_nano/src
git submodule add https://github.com/petrasvestartas/wood.git
cd wood
sudo '/home/petras/brg/2_code/wood_nano/src/wood/install_ubuntu.sh'
```

For update:

```bash
git submodule update --init --recursive
# git submodule foreach git pull origin main
sudo rm -r build
```


Link wood dependencies to nanobind
----------------------------------
-   Ubuntu - linked, Check: a) PCH is not speeding the build, b) SQL has no be unlocked like this ```sudo chown -R```




Code wrapping
-------------


-   for development you need to use pip install . and even you changed __init__.py
-   function based on the EDX tutorial
-   Process:
        -   add c++ and binded method in nanobind_binding.cpp
        -   run pip install -e . to check if there are no C++ mistake
        -   import the method in src/wood_nano/__init__.py
        -   test the imported method in tests/test_basic.py
        -   compas_wood - create a file called src/compas_wood/binding/binding_read_xml_polylines.py
        -   compas_wood - add this name in __init__.py
        -   compas_wood - fill the contents of the file and create a test under if __name__ == "__main__"
        -   compas_wood - write docstrings under the method
        -   compas_wood - invoke docs and check the result



compas_wood
-----------


```bash

conda config --add channels conda-forge
conda create -n compas_wood_3_9_10 python==3.9_10 compas
conda activate compas_wood_3_9_10
conda install build setuptools wheel twine 
sudo apt install twine or conda install twine
cookiecutter gh:compas-dev/compas_package_template
export PATH="~/anaconda3/envs/compas_wood/bin:$PATH"
sudo apt install invoke
pip install -r requirements.txt
```

-   add requirements wood-nano
-   rewrite examples
-   compas_wood must be installable by ```pip install compas_wood```
-   documentation based on edx tutorials
-   create compas_model with vizualization
-   upload to pip https://github.com/petrasvestartas/compas_snippets


PyPI Release
------------

Releases are automated via GitHub Actions using trusted publishing.

**One-time setup (PyPI):**
1. Go to https://pypi.org/manage/account/publishing/
2. Add pending publisher with:
   - Project: `wood_nano`
   - Owner: `petrasvestartas`
   - Repository: `wood_nano`
   - Workflow: `release.yml`
   - Environment: *(leave blank)*

**To publish a release:**
```bash
git tag v0.2.0
git push origin v0.2.0
```

This triggers the `release.yml` workflow which builds wheels for all platforms and publishes to PyPI.

MAC GIT CONFLICT RESOLVE
------------------------

To resolve Git conflicts on a Mac, follow these steps:

1. Print the Python path for compas_rhino:
    ```bash
    python -m compas_rhino.print_python_path
    ```

2. Install the package using pip:
    ```bash
    sudo -H /Users/petras/.rhinocode/py39-rh8/python3.9 -m pip install .
    ```

3. Install the package with the in-tree build feature:
    ```bash
    sudo -H /Users/petras/.rhinocode/py39-rh8/python3.9 -m pip install . --use-feature=in-tree-build
    ```

In this case, the default message is pre-filled, but you can modify it if needed. To proceed with the merge and accept the default commit message, you can follow these steps:

1. Press `i` on your keyboard to enter insert mode in the text editor.
2. Make any changes to the commit message if necessary.
3. Once you're done, press `Esc` to exit insert mode.
4. Type `:wq` to save the commit message and exit the text editor. If you're using Vim, this command writes the changes and quits the editor.