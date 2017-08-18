# ProceduralWorld
# Author: Taylor Driggs
# Start Date: 8/18/17
#
# Description:
#
# This project was originally intended to be a procedural city generator but I decided that in order to have procedurally generated cities, I needed a procedurally generated world. Currently, the world generates using a Voronoi diagram and pulls from OpenSimplex to generate noise to use as the base of the randomization.
#
#
# Goals:
#
# Eventually, I would love to move to spherical Voronoi diagrams and turn this into an actual planet. Before I do that, however, I need to nail down elevation, biomes, rivers, etc. There is still a lot of work to do before that point. I also want to switch from pygame to actual OpenGL graphics, but I'm not really too worried about that yet.
#
#
# Sources:
#
# Most of my the logistics including the graph structure and the use of Voronoi diagrams came from this site. I don't follow all of the standards that are set in this blog post mainly because I want to write the code myself and push myself to optomize it my way. Also, it uses ActionScript, which is something that I really don't want to dive into at the moment. I'd much rather stick with good'ol'python!
#
# http://www-cs-students.stanford.edu/~amitp/game-programming/polygon-map-generation/
#
#
# Usage:
#
# If you want to download this project and modify it and use it yourself, feel free to! I recommend using virtualenv to set up your workspace. Also, I know there are some problems right now with scipy and its spatial package. I believe it is due to not having the qhull library properly installed and linked on my machine. I want to avoid doing that though, so I'm am currently on the lookout for a better Voronoi diagram and convex hull library; or maybe I'll just write my own!
#
#
# Contact:
#
# If you need to contact me for any reason (questions, recommendations, etc.) feel free to message me here on GitHub or email me at taylor.a.driggs@gmail.com.
#
#
# About Me:
#
# I am a junior in the Digital Simulation and Gaming Engineering degree at Shawnee State University in Portsmouth, OH. I currently work at Zebu Compliance Solutions, also in Portsmouth, OH as a database engineer. I'm still learning a lot about professional software development, so if you notice bad practices in my code, please point them out!
