# What it looks like?

https://public.ryichando.graphics/~ryich/webpapers/example/sample.html

# Why this thing is good?

Simple and fast. Everything is on the browser; you can access the whole contents from anywhere (even with a smart phone when you are out of office) if you put it on a private web server (e.g., VPS/NAS). You may also share with collaborators via links. Of course you can locally use it if you do not own a private server.

# How to use

For each paper, create a directory containing

  - A paper PDF, ending with `.pdf`
  - A bibtex file, ending with `.bib`
  - Supplemental materials

Put them into the `papers` directory.

### A directory layout example

    papers
    ├── ...
    ├── authors2021             # Some recognizable unique short name
    │   ├── main.pdf            # Paper main PDF file (it does not have to be main.pdf if a single PDF is given)
    │   ├── citation.bib        # BibTex file containing the paper info (any name ending with .bib is fine)
    │   ├── video.mp4           # Video file
    |   └── ...                 # Supplemental materials
    └── ...

A corresponding layout for the example page can be seen at https://public.ryichando.graphics/~ryich/webpapers/example/

Next, run the following commands

```bash
docker-compose build
docker-compose run --rm webpapers python3 main.py papers
```

This can take a while depending on how many papers you have. When complete, `index.html` will be generated in the `papers` directory, which you can browse on your favorite web browsers. You may edit `config.ini` in the directory to change settings.

# Some rules

  - When multiple PDFs are provided, `main.pdf` should be the primary paper PDF

# Cleaning

```bash
docker-compose run --rm webpapers python3 main.py papers --clean
```
to clean generated files.
