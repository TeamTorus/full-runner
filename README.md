
# Team Torus - Full Runner
This code contains the central system for the shape optimization loop, currently written for airfoils. Implements logic tying together the genetic algorithm, meshing, and CFD, along with parallel processing jobs across cores and data collection. It connects to a remote PostgreSQL database, which is usually hosted on AWS RDS.

## Getting Started
After cloning the repo, a few core libraries will need to be installed. Run `pip install -r requirements.txt` in the root directory to install these.

In order to setup config variables for the run, modify the config variables at the top of the `scheduler.py` file, found [here](./scheduler.py#L15). These determine the parameters for the shape optimization, which are as follows:
- `shape`: What shape is being optimized for (for the database)
- `solver`: What kind of solver is being used for CFD (for the database)
- `optimizer`: What optimizing method is being used (for the database)
- `mesh_radius`: The mesh resolution for the Salome mesher
- `total_generations`: The total number of GA generations to run
- `population_size`: The population size of each generation
- `alpha`: The learning rate of the GA
- `slope_weight`: How much to weight the slope factor of the cost function
- `input_file`: The input text file for the initial control points/parameters
- `cores`: The number of cores to run the process on

In order to run the system, you need to enable the local environment that Salome needs. This can be done by running `source` on the `env_launch.sh` script that Salome has, which for the remote desktop specifically is:
```
source ~/salome/SALOME-9.12.0/env_launch.sh
source ~/salome2/SALOME-9.12.0/env_launch.sh
```
In order to connect to the remote database, a `.env` file with the RDS connection details is needed. In addition, a `faces` file needs to be added to the [`polyMesh` folder](./structure/airfoilOptTest1Clean/constant/polyMesh), as this is not in the repo (for file size reasons). You can use `scp` to copy these files into the deployment environment.

In order to use `git` on a Windows computer for development and deploy on a Unix system, you need to standardize the file endings and carriage returns. To do this and disable CRLF conversion, run 
```git config --local core.autocrlf false```

The main file to run is `scheduler.py`, which can be directly run. In order to run it in the background of a Linux system as a daemon, you can use `nohup` or `disown` to disconnect the process from the current shell environment. This can be done as follows:
```
python ./scheduler.py &
jobs -l
disown -r
```

## How it works
to be written

## Database Format
In order to keep the data persistently in a remote location, the data is stored into multiple tables in the RDS database. The main table, called `runs`, stores the data of every full run of the optimizer that has occurred or is in progress, as well as holding the name that links to the table that stores that run's specifics. The schema is as follows:

Table `runs`:
|   run_id | time_started               | time_completed             | in_progress   | completed   | table_name   | shape   | solver     | optimizer   |   num_generations |   population_size |   resolution |
|---------:|:---------------------------|:---------------------------|:--------------|:------------|:-------------|:--------|:-----------|:------------|------------------:|------------------:|-------------:|
|Primary Key | Datetime | Datetime| Boolean| Boolean| String   | String| String| String | Integer |Integer | Integer |

The `table_name` entry for each row corresponds to another table with that same name, which stores the details of that run specifically and each of its individuals, with the following schema:

Table `table_name`:
|   individual_id | time_started               | time_completed             | in_progress   | completed   |   generation_number |      fitness |           cl |             cd | ctrl_pts    |
|----------------:|:---------------------------|:---------------------------|:--------------|:------------|--------------------:|-------------:|---------------:|---------------:|:------------|
Primary Key | Datetime | Datetime| Boolean| Boolean| Integer |Integer | Integer  | Integer | JSON |


## Data Collection
You can monitor and see the progress of the run while it's going or after the fact by accessing the remote database on RDS, and using SQL to query it and retrieve results. The [dbviz.py](./dbviz.py) file contains functionality to automatically do a few standard queries and display the data. The file can be run as follows:
```
python3 dbviz.py [-FlagOptions]
```
By default, running this with no flags or options will print out the latest run's table, as well as what the best shape from that iteration is. Adding flags (one or more), space delimited, can change and configure this behavior. Adding options to certain flags can allow for certain behavior.

### Flag Options
#### `-runs`
Displays the `runs` table with all runs and their data
#### `-fulltable [table_name]`
Displays a given table, with the name passed in as an option following the flag. 
#### `-t [table_name]`
Displays a given run's table as well as what its best shape is. The name of the table should be passed in as an option following the flag.
#### `-s [start]` 
Specifies the starting individual_id when querying the table. 
#### `-e [end]` 
Specifies the ending individual_id when querying the table. 
#### `-i [individual_id]` 
Displays information about a specific individual identified by its individual_id, instead of the best shape.
#### `-p [individual_id]` 
Plots the airfoil of the individual identified by its individual_id. If no individual_id is provided, it plots the airfoil of the individual with the maximum fitness. 
#### `-track [generation_interval]` 
Plots the airfoil for each generation at the specified interval. If not specified, it defaults to plotting the airfoil for every generation. 
#### `-plotfile [file_path]` 
Specifies the file path to export plots to. If done in conjunction with `-p`, it specifies the relative path and file name to save the plot to. If done with `-track`, it should specify a folder location to which to save these images.
#### `-graph` 
Plots the fitness over the generations graph.

-------------------------------------
For example, to see the output of table `airfoilGA122`, for individuals 50 through 100, and save the plot of the best airfoil in this range to a file called `image.jpg`, run:
```
python3 dbviz.py -t airfoilGA122 -s 50 -e 100 -p ./image.jpg
```
