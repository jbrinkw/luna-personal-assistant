[[Projects/gamegenai/OLD|OLD]]

Purpose:
This project aims to build all the piece of the infinite text driven generation of a playable 3d world with interactable story and characters.

why tf am i trying to make a 3d world first

Planned stack

world gen:
- city generator that creates a segmented map of the of the city with sreets, building footprint, park layouts etc. just a 2d map of the layout of the city
- floorplan generator creates the internal floor plan and layout inside of the building. 
- furnishing model lays out all the funisture and creates the models
renderer:
- instaed of creating all the graphic for each object and setting up lighting like a normal game this will primary work on a game world that is just color coded object for like tree, house car etc and will have an ai that takes that mask and renders it to look realistic
- each indicualy object will have its bases tag for what it is and then optional semantic embedding metadata that can modify how it is rendered
- the render will also have a field to change the global rendering theme (maybe ill just code that into the metadata for each object buti think this make more sense)
interactive agents:
- the world will be full of interacive characters that simulate real behivor by a detailed back story and coded wants and needs stats that they will be driven to statisfy themselves
- they will need some way of seeing the world in realtime as they move around for starters im thinking they should have a mutli level reaction system. like one will be very fast and will just get a stream of notications of event and thing in thier sight in liek 2 second blocks and the fast brain will router stuff im to the next level if it thinks it is worth interacting with. then the higher level brains can figure out what to do with that. 

notes:
- not all objects will be untextured but even if they are the render will be able to override it. 
