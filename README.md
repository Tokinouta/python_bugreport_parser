# Bugreport Parser

This is an attempt to automize the analysis of Android bugreports. There are too many vanilla cases that contain no effective information of the reported issue. Such a script will spare me more time on such dull stuffs.

## Project architecture

Currently, there are two main components. 

- bugreport: This models the bugreport zip and its contents inside, accompanied by some basic loading, parsing and searching functionality
- plugin: This extends the ability of checking specific causes of issues

Under construction. Use with causion.
