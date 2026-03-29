#!/bin/bash

# Create a new Jekyll environment
# check if the conda environment already exists
if conda info --envs | grep -q 'jekyll_env'; then
    echo "Conda environment 'jekyll_env' already exists. Activating it..."
else 
    echo "Creating new conda environment 'jekyll_env'..."
    conda env create -f jekyll_env.yaml
fi
conda activate jekyll_env

# Install Jekyll
gem install jekyll
gem install bundler:2.7.2

# update the information
python scripts/sync_cv_sections.py

# test the installation by building a new Jekyll site
# Use Bundler 2.7.2 explicitly and silence the CLI warning
bundle _2.7.2_ config set default_cli_command install --global
bundle _2.7.2_ install

# Serve the site using the pinned Bundler version
bundle _2.7.2_ exec jekyll serve --trace --open-url --livereload
