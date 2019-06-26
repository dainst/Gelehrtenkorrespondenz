# Importing data into Neo4j

## Prerequisites

* Python 3.7
* Docker
* LXML [Prerequisites](http://lxml.de/installation.html).

## Linux and MacOS

### Installing the Python dependencies

This subdirectory contains its own [requirements.txt](requirements.txt).

### Starting Neo4j

With Docker installed, simply run:
```
docker run -p 7474:7474 -p 7687:7687 -v $HOME/.neo4j/data:/data -e NEO4J_AUTH=neo4j/<password> neo4j:3.4.0
```
While replacing <password> with whatever you want to use as your database's root password. 

Once started you can access its database browser at 
[http://localhost:7474/browser/](http://localhost:7474/browser/).

#### Importing data

There is already example data included in the repository. You can either import a single TSV file (see `./tsv_data`) or
a single/multiple EAD files (see `./ead_data`). 

If you setup the dependencies in a Python virtual environment (venv, see above), first activate the environment: 
`source <path to venv directory>/bin/activate`. 

To start the import run __import.py__ (here importing all EAD files):

```
python3 graph_db_imports/import.py ./graph_db_imports/ead_data localhost 7687 <username> <password>
```

#### Deleting data

For deleting all data in the database open the database [browser](http://localhost:7474/browser/) and run the following 
query:
 
```
MATCH (n) DETACH DELETE n
```
