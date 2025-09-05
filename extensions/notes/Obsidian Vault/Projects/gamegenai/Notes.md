8/24/25
so the multi agent minecraft sim is cool but i think its going to add extra complexity compared to just using my own env where ik how everything wroks and it would be a lot easier to add extra ffeature. i dont need a complex env but the whole point of this project is how the agents will interact and collaberate in a survival env

8/23/25
this is kinda turning into more of ecoai but ig this is more centered around llm driven social interaction. so my goal with this project is to create a society of ai agent that work and interact at a natural human speed. this will require me to create a multi level ai brain that will allow the agent to react to the world in realtime with a fast model and still have high level planning with a slower smarter model. simular to project sid. i think an intresting twist to this would be giving the agent buildable instints where they can create a graph of common actions to automate their common routines. that would play into pretty much all my other projects

it would be cool if i used a rl modle for world interaction that the llm had to guide. that is almost definatly the future of physical ai agents. how would that even work. like would i have to train the rl agent on basic tasks .ok this is actually cool. i cant train a basic rl agent for all to fundemtall actions that the llm can trigger the goal of the rl agent. also i can probaly natualy have skill levels by adding noise to the rl agent for low level skills and the gradually removeing that noise as the agent gains skill points. tahts a really fucking cool idea i love. I could either train a seperate model for each skill or i could train one model. i was thinking sperate bc that makes the leveling skill system simpler bc i can just add noise to that one model but maybe i dont really need to seperate it like that bc i can change the level of noise based on the current adjecttive

so im stuck on whether or not i want to build my own env. the repo im looking at rn would probaly have all the feature i could want for this project besides. if i were to use this project i would want to

8/22/25
ok so the main goal is having an infinite text driven game the biggest thing holding back at the moment is an end to end ai system like some of the demos but they aren't close to a full story driven game like im tihnking about. house gen is close to what i had in mind but it doesnt have a way to modify post gen beside reprompting. i dont think text driven modification is really neccacery for a v1 release. that alone could be cool. i think something i was struggiling with before was complex descriptions for the house with adjectives and shit but i dont think that is really nessacery because i can get an optionally complex descritpion and then just extract the deatil for the floorplan and feed that into the floor plan get and then segment all the other details by room and use that for the furnisiging agent. yeah? idk what else there would be to it. the furnishing ais looked good from a glance. one thing the house tune doesnt do that is import is take an outer footprint as a constraint. this isnt a dealbreaker but it is definalty a limiting factor becuase in world gen it would require me to have generous boudires around each generation and a lot of deadspace to prevent overlaps. that could be intresting if i could remake it with a the boundy constraint. also finetuning it on the diffrent level of generations like city and neiborhood could be intresting.this is a preety deep problem the more i think about it. like how am i going to create the descriptoins for the nieborhoods and citys? how do you even descibe the layout of that. what if i just used real locations and just used an ai for find a location that fit a descriptions. how woujld this even work. i think they were on the right track with voxel driven diffsion

 i think the future of this project is going to be generating the world of 3d color coded objects the maybe some of them with textures or not and then haveing a rerender on top that actually adds the detail. i really like that its modular and add a deminsion of customisablity. at some point each object could have optional extra emembedding data to modify its rendering. like there could be a color code for house and then a specic object could have extra emmbedding to render it as run down or covered in bullet holes. then as the player walks arond the projections can be saved and 

rerender color codes https://urbanarchitect.github.io/

im lost what am i doing. i was reaseraching how to accoumplish the generation of the 3d worlds. it looks like there are models that can create a floor plan in a boundy and models that can create city layouts so isnt that all i need? i think im lost looking at the model archatectume of some of these papers it look forieng to me. i should know how all of that works. anyways if that all i need is the next step not just to combine it?

maybe a cool first project would be to ignore unique city gen and just use the real world. make a simple segmentation map to color code real places and then use the floorplan generator to create the interious and the renderer to add texture. maybe and advancement i could make to floor plan generators is generaize them to any kind of building or teach them how to make multi level buildings. those are decent ideas for an actual reaserach paper. i am a little more intrested in expirementing with interactive agents i would definatly enjoyreseraching the sota for socity simulation. and it could potentially be simpler than the inifite world gen part of this project which will probaly be very software enginnering heavy. i could also look into the renderer and explore how i could implent memory of is generations and then also added semantic tags to objects

im definating overcomplicating this by trying to figure out a 3d world but then again the only 3d thing so far has been the renderer. yk this might actaully be doable with a simple top down pokemon style game. 

i think a game with a powered characters even a graphiclly very simple one could be very appealing as long as there was a decent amount of neuance to what the characters could do so what is the simplest version of this project i can make 

OK i really like the idea of v1 being a pokemon type map where there it loads one screen at a time and you can enter buildings and it reload the env and you just walk to the edge of the screen to go to the next area. 

im getting lost trying to figure out everyting at the same time i need to break this down. there are 3 things the world gen the agents and the story and game ascpect to it. i think for now i should just ignore the game ascpet and work out making the world then in a way that would allow for agents and a player to move around the pokemon map style idea is good but i feel like it might almost be more difficult maybe i should just completed forget the render too for now i just try to make a segmenation map of the would with coded rules about that the agnets can walk on. 

i was going to say that minecraft is cool but its not really a good place for my infinte text driven world but it actually could be and if that project were successful it would be massively popular and accessble. i wouldn't nesscerly need a minecraft text to 3d to mess around with the agents

so minecraft seems cool in concept but i dont think it would be good for anything but agent simulaion not 3d world stuff. theres definalty potential in the world gen with minecraft but the

current project ideas:
- retrain the floorplan to do multi story
- improve the minecraft socity 
- make minecraft socity interactive
- problay not the renderer thats definatly gonna be over my head and i would need to have world to use it on first

im definalty considering going donw the agent society path instead of the 3d world path. th eonly intresting porject i can think to do with the 3d world would be the multi plevel floorplan which would definatly be cool but woorking on agent society sounds like way mor efun probaly also a lot more complicated.. mybe i should jsut tdo the multi level floor plan 

ahhh there is too much to think about im lost. 3d world is out of scope for now if i did anything with that i would be the multi story mod. multi agents systems would defintaly be complicated. there are too many options for frameworks and idek what exactly i want my bare min requriments to be. like do i just want the agents to move around in a small

