# What it looks like?

https://ryichando.graphics/webpapers_sample/

# Why this thing is good?

Everything is on the web; you can access the whole contents from anywhere (even with a smart phone when you taking a walk) if you put it on a private web server (e.g., NAS). You may also share with collaborators. It's also free, simple and fast.

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
    │   ├── main.pdf            # Paper main PDF file
    │   ├── citation.bib        # BibTex file containing the paper info
    │   ├── video.mp4           # Video file
    |   └── ...                 # Supplemental materials
    └── ...

Next, run the following commands

```bash
docker-compose build
docker-compose run --rm webpapers python3 main.py papers
```

`index.html` will be generated in the `papers` directory, which you can browse on your favorite web browsers. You may edit `config.ini` in the directory to change settings.

# Some rules

  - When multiple PDFs are provided, `main.pdf` should be the primary paper PDF
