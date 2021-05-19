# How to use

For each paper, create a directory containing a paper PDF and supplemental materials. Put them into the `papers` directory. Next,

```bash
docker-compose build
docker-compose run --rm webpapers python3 main.py papers
```

`index.html` will be generated in the `papers` directory, which you can browse on your favorite web browsers. You may edit `config.ini` in the directory to change settings.
