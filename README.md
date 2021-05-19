# What it looks like?

https://ryichando.graphics/webpapers_sample/

# How to use

For each paper, create a directory containing
  - A paper PDF, ending with `.pdf`
  - A bibtex file, ending with `.bib`
  - Supplemental materials
Put them into the `papers` directory. For example,
    
### A directory layout example

    papers
    ├── ...
    ├── authors2021             # Some recognizable short name
    │   ├── main.pdf            # Paper main PDF file
    │   ├── citation.bib        # BibTex file containing the paper info
    │   ├── unit                # Video file
    |   └── ...                 # Supplemental materials
    └── ...

Next, run the following commands

```bash
docker-compose build
docker-compose run --rm webpapers python3 main.py papers
```

`index.html` will be generated in the `papers` directory, which you can browse on your favorite web browsers. You may edit `config.ini` in the directory to change settings.

# Simple Rules

  - When multiple PDFs are provided, `main.pdf` is set as the primary paper PDF.
