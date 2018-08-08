# Importing data into Neo4j

## Prerequisites

* Python 3.7
* Docker
* LXML [Prerequisites](http://lxml.de/installation.html).

### Linux and MacOS

#### Installing Python 3.7 with _pyenv_

For Ubuntu 18.04 and many other OS is not recommended to upgrade the pre-installed Python version. For example, Ubuntu
probably will not update the the pre-installed major Python version, since too many scripts and programs depend on it!

To use new newest Python version or multiple versions at the same time you could install _pyenv_
(https://github.com/pyenv/pyenv). To create isolated Python environments with _pyenv_ you could use
_pyenv-virtualenv_ (https://github.com/pyenv/pyenv-virtualenv).

#### Installing Python dependencies

##### Option a) Create a virtual Python environment with _pyenv-virtualenv_

This is recommended for most cases and assumes you are using Linux or MacOS.

1. Install _pyenv_: https://github.com/pyenv/pyenv#installation
2. On Linux OS check file `~/.bashrc` (or `~/.bash_profile` or `~/.zshenv` depending on the OS) for _pyenv_
Configuration. If necessary, add the following at the end of the file:
   ```
   export PATH="~/.pyenv/bin:$PATH"
   eval "$(pyenv init -)"
   eval "$(pyenv virtualenv-init -)"
   ```
   Restart your shell so the path changes take effect:

   `$ exec "$SHELL"`

3. Install Python: `$ pyenv install 3.7.0`
4. Create a virtual Python environment with _pyenv-virtualenv_ (https://github.com/pyenv/pyenv-virtualenv):

    a) `$ pyenv virtualenv 3.7.0 virtual-env-3.7.0`

    b) Switch to the Python project directory where you want to use the virtual Python environment
    (e.g. `~/workspace/Gelehrtenkorrespondenz/`)

    c) Activate the the virtual Python environment: `$ pyenv local virtual-env-3.7.0`

    d) Install the project dependencies while inside the virtual environment:
    `pip3 install -r graph_db_imports/requirements.txt`.

##### Option b) Install into Python virtual environment with _venv_

If you have already installed Python 3.7.x (or higher) globally you could use _venv_ to create a virtual Python
environment.

1) Create a virtual Python environment by executing `python3 -m venv venv/` in the project's root directory.
2) Start the virtual environment: `source venv/bin/activate`.
3) Install the dependencies while inside the virtual environment: `pip3 install -r graph_db_imports/requirements.txt`.

## Starting Neo4j

With Docker installed, simply run:
```
docker run --publish=7474:7474 --publish=7687:7687 --volume=$HOME/.neo4j/data:/data --env NEO4J_AUTH=neo4j/<password>
neo4j:3.4.0
```
While replacing <password> with whatever you want to use as your database's root password. 

Once started you can access its database browser at 
[http://localhost:7474/browser/](http://localhost:7474/browser/).

## Importing data

There is already example data included in the repository. You can either import a single TSV file (see `./tsv_data`) or
a single/multiple EAD files (see `./ead_data`). 

If you setup the dependencies in a Python virtual environment (venv, see above), first activate the environment: 
`source <path to venv directory>/bin/activate`. 

To start the import run __import.py__ (here importing all EAD files):

```
python3 graph_db_import/import.py ./ead_data localhost 7687 <username> <password>
```

## Deleting data

For deleting all data in the database open the database [browser](http://localhost:7474/browser/) and run the following 
query:
 
```
MATCH (n) DETACH DELETE n
```
