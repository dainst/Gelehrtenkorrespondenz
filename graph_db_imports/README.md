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
```bash
docker run -p 7474:7474 -p 7687:7687 -v $HOME/.neo4j/data:/data -e NEO4J_AUTH=neo4j/<password> neo4j:3.4.0
```
While replacing <password> with whatever you want to use as your database's root password. 

Once started you can access its database browser at 
[http://localhost:7474/browser/](http://localhost:7474/browser/).

#### Importing data

There is already example data included in the repository. You can either import a single TSV file (see [./tsv_data](tsv_data)) or a single/multiple EAD files.

EAD files are exported from the [Kalliope database](https://kalliope-verbund.info/) where metadata on the letters was originally entered. You can download these dumps [from confluence](confluence:8090/pages/viewpage.action?pageId=29786709) (Downloads are marked in red as "aktuell".) Extracting the archives you should have six .xml files in one directory, the first five representing the Berlin collection and the last representing the Rome collection:

```
ead_DE-2322_10285.xml
ead_DE-2322_4632.xml
ead_DE-2322_4685.xml
ead_DE-2322_70322.xml
ead_DE-2322_70459.xml
ead_DE-2490_65759.xml
```

To start the import run [import.py](import.py) (here importing all EAD files):

```bash
python3 graph_db_imports/import.py ./path/to/ead_data localhost 7687 <username> <password>
```

#### Deleting data

For deleting all data in the database open the database [browser](http://localhost:7474/browser/) and run the following 
query:
 
```
MATCH (n) DETACH DELETE n
```

##### Updating data

For updating data first copy the updated EAD data into [ead_data](ead_data), then delete the existing data in Neo4j and finally (re-)import all EAD files. You should probably also push the updated EAD files to Github.
