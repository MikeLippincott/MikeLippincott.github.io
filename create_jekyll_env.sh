#!/bin/bash

# Create a new Jekyll environment
conda env create -f jekyll_env.yaml
conda activate jekyll_env

# Install Jekyll
gem install jekyll bundler

# test the installation by building a new Jekyll site
bundle exec jekyll serve
