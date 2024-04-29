# full-runner

`git config --local core.autocrlf false` # Disable CRLF conversion

manually add in ./structure/airfoilOptTest1Clean/constant/polyMesh/faces

manually add in .env file & route to source salome if applicable

if error, try clearing the `runtime/` folder for all files but `base`

implements concurrency control via row-level locking and optimizes SQL lookups via generation number table partitions