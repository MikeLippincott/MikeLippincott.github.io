set shell := ["bash", "-cu"]

# Create and sync the local uv environment with all project dependency groups.
env:
  #!/bin/bash
  # check if the conda environment already exists
  if conda info --envs | grep -q 'jekyll_env'; then
    echo "Updating conda environment 'jekyll_env'..."
    mamba env update -f jekyll_env.yaml
  else
      echo "Creating new conda environment 'jekyll_env'..."
      mamba env create -f jekyll_env.yaml
  fi
  conda activate jekyll_env
  # Install Jekyll
  gem install jekyll
  gem install bundler:2.7.2

update_site:
  #!/bin/bash
    # update the information
    conda activate jekyll_env

    python scripts/sync_cv_sections.py

bundle_install:
    #!/bin/bash
    conda activate jekyll_env
    # test the installation by building a new Jekyll site
    # Use Bundler 2.7.2 explicitly and silence the CLI warning
    bundle _2.7.2_ config set default_cli_command install --global
    bundle _2.7.2_ install

    # Serve the site using the pinned Bundler version
    bundle _2.7.2_ exec jekyll serve --trace --open-url --livereload

all:
    just env update_site bundle_install
