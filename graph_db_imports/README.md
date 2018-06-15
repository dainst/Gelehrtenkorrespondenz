# Importing data into Neo4j

## Prerequisites

* Python 3.5
* Docker

To install the Neo4j Python driver run `pip3 install neo4j-driver`.

## Starting Neo4j

With Docker installed, simply run:
```
docker run --publish=7474:7474 --publish=7687:7687 --volume=$HOME/.neo4j/data:/data --env NEO4J_AUTH=neo4j/<password> neo4j:3.4.0
```
While replacing <password> with whatever you want to use as your database's root password. 

Once started you can access its database browser at 
[http://localhost:7474/browser/](http://localhost:7474/browser/).

## Importing data

A TSV file containing metadata is already included in the repository. To import the data into Neo4j run 
__import.py__:

```
python3 import.py ./gelehrtenbriefe_metadata.tsv localhost 7687 neo4j <password>
```

## Deleting data

For deleting all data in the database open the database [browser](http://localhost:7474/browser/) and run the following 
query:
 
```
MATCH (n) DETACH DELETE n
```