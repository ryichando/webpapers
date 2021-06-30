# What it looks like?

https://public.ryichando.graphics/~ryich/webpapers/example/sample.html

<img src="https://raw.githubusercontent.com/ryichando/webpapers/master/resources/realtime_search.gif" alt="demo" width="350">

# Why this thing is good?

Simple and fast. Everything is on the browser; you can access the whole contents from anywhere (even with a smart phone when you are out of office) if you put it on a private web server (e.g., VPS/NAS). You may also share with collaborators via links. Of course you can locally use it if you do not own a private server.

# Realtime search

Paper texts are easy to explore using a new realtime search. Everything operates on JavaScript; no server configuration is needed to get this working.

# Setting up

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
docker build . -t webpapers
docker run -v ${PWD}:/root --rm webpapers papers
```

This can take a while depending on how many papers you have. When complete, `index.html` will be generated in the `papers` directory, which you can browse on your favorite web browsers. You may edit `config.ini` in the directory to change settings.

# Some rules

  - When multiple PDFs are provided, `main.pdf` should be the primary paper PDF
  - If you want to search only from titles, start with "title:" and type keywords

# Cleaning

```bash
docker run -v ${PWD}:/root --rm webpapers papers --clean
```
to clean generated files.
