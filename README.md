# What it looks like?

https://ryichando.graphics/webpapers_sample/

# Why this thing is good?

It's free, simple and fast. Everything is on the web; you can access the whole contents from anywhere (even with a smart phone) if you put it on a private server. You may also share with collaborators.

# How to use

For each paper, create a directory containing

  - A paper PDF, ending with `.pdf`
  - A bibtex file, ending with `.bib`
  - Supplemental materials

Put them into the `papers` directory.

### A directory layout example

    papers
    ├── ...
    ├── authors2021             # Some recognizable short name
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
