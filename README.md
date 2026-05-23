# extract_images_gathering_tool
a set of tools to gather image training data for an AI model (or for some other purpose)

# Why?
The process of getting data for training an AI model is hard if you're not a large organisation.

# Aren't there better tools available for that already?
Probably.

# Overview
## ddg_images.py
seaaches for images that fit the queries and downloads them
## pdf_extract.py
extracts images from a pdf from specified pages
## duplicates.py
a tool to delete similar images
similarity is calculated by resizing to 512x512, hashing the image and calculating how close the differing bits are (Hamming distance)

# DISCLAIMER
This project was vibe coded.
