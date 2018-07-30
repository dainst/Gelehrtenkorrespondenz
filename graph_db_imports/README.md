# Importing data into Neo4j

## Prerequisites

* Python 3.5
* Docker
* LXML [Prerequisites](http://lxml.de/installation.html).

### Installing Python dependencies

#### Option a) Install into Python virtual environment (venv)

This is recommended for most cases and assumes you are using MacOS or Linux.

1) Create a Python virtual environment by executing `python3 -m venv venv/` in the project's root directory.
2) Start the virtual environment: `source venv/bin/activate`.
3) Install the dependencies while inside the virtual environment: `pip3 install -r graph_db_imports/requirements.txt`.

#### Option b) Install Python dependencies globally

If you want to install the dependencies globally, just run `sudo pip3 install -r graph_db_imports/requirements.txt`

## Starting Neo4j

With Docker installed, simply run:
```
docker run --publish=7474:7474 --publish=7687:7687 --volume=$HOME/.neo4j/data:/data --env NEO4J_AUTH=neo4j/<password> neo4j:3.4.0
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