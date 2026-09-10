FROM postgis/postgis:16-3.4

# Copy initialization scripts (run on first startup)
COPY ./init/ /docker-entrypoint-initdb.d/

EXPOSE 5432
