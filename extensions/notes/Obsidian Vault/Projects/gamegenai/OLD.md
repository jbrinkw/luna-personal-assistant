oasis is cool but i think they are going about that wrong. right now they dont have any memory so the model wont remember what you place if you turn your head away. I think their plan is just to save frames and feed them back in for memory. i think the better way to go about this is to create an embedding of the env that is updated when the model sees something new and is fed into every step so the model can remember the things around it. this has the added benfit of being able to easily change the models world. if you have an emmbedding model that can compress and remember the world around it i dont think it would be to hard to make a text driven editing model from there. i feel like a super basic version of this should be within reach of me after a few weeks of studing hard. this would be game changing if i could figure it out.

  

anouther benefit is that it could sigficantly increase proformance because if the model is remembering the data it generates it doesnt constantly have to make new stuff

on second thought maybe it would be better to focus on saving an env and dynamically generating the env in an embedding and then build the agents view renderer on top of that but at that point wouldn’t it just be easier to generate the world in a more descrite way … it wouldn’t be the same a saving the world in a more descrete way because the embedding would just be latent repusentation of the ideas of each piece of the env and the render would be converting that latent view into whatever filter it is set for. im thinking that the latant env would be a 3d latent space that is the ideas of what it is but and that could be converted to anything by a filter on the render ai but i think any changes to the type would just be a traversion of the latent space of the env in some direction

  

  

So what do i need to study… probaly diffision and transfromer models at a high level and all of the ways to modify them. i feel like im going to need to have a really good understanding of how embeddings work and how they can be manuliplated. so i think ill skip to the end of fast ai part 2 and then find a new course or reseach from there to get a good feeling for how to mess around with transformers and diffuion models

  

recap 11/7

I think the best way to approach this problem is to have a network for storing a latent repusentation of the env and a model for converting it to whatever style it was trained for. I was thinking that style would be built into the env network but i think it would be simpler to have the env network be a general repusentation and the renderer trained for a specific style. like how you can make a sketch and an image model can fill it in and make it realistic. except the sketch is a latent network of the env. hopefully shouldn’t be to hard to add text driven generation to the env network later

  

i feel like i might not be thinking this all through if this is supposed to be using the skech to art idea the env would pretty much just be a 3d block | voxel map and then the renderer would just be adding texture and effects. i dont think thats really what im shooting for. its not an awful idea but that would leave all of the generation to the evn generator and thats new tech im not going to be able to make. maybe a better idea would be to keep all of the generation in the renderer and have the env embedding be created by basically doing a single point 3d scan. like as the renderer is going there is a seperate model doing a 3d scan and build

  

methods: ground video models in a history of their own generation

sketch to art: idk how to make a 3d env generator directly

3d scan: kinda sounds like a nerf? i have no idea how to attach that to a video model

  

11/8

i think im in over my head with this idea… i think i have the right apporach but this is definately on the more advanced side of stuff. I think i should continue learning high level concepts until ive gotten enough of the puzzle pieces to figure this out. what im thinking about what actually be far more impactful than i orginally thought because this could be applied to any transformer/diffsion network. its bascially a high dimenstional memory array. kinda like and emmbedding db? idk how that works. i think it just runs the users input though an embedding gen and find stuff close to it in the db and retruns it as context. what im thinking about is just the next version of that? i really need to get back to the fundementals and keep this in mind as i go because i definately dont have all the background i need

  

  

resources:

[https://openai.com/index/video-generation-models-as-world-simulators/](https://openai.com/index/video-generation-models-as-world-simulators/)

[https://oasis-model.github.io/](https://oasis-model.github.io/) technical report

  

old

[https://platform.maket.ai/projects/670ce4b385095c255857c54c/floorplan-generator?tool=floorplan-generator](https://platform.maket.ai/projects/670ce4b385095c255857c54c/floorplan-generator?tool=floorplan-generator)

doesn’t seem like theres been any real advancement in floorplan generation.

it definately got better with 4o it would probaly be really good with o1 to the point where i would have to reengineer stuff to add more features



[[synthetic data- tests]]

text to svg models could be a great tool to generate layouts as they work with descrete shapes but they might suffer from the same problems as other text to image models where they arn’t really trained with spatially orienteted data.

the [https://compass.blurgy.xyz/](https://compass.blurgy.xyz/) paper seems to be a good start. i might need to reimplemnt thier code but with the new models that shouldn’t be too hard. I also really like using chess as a benchmark. i think it might be better to use has a post training test than using it in training. for training models have probaly gotten good enough at describing

  

  

  

  

  

what if i make an agent for every entity and space. like each person will be its own agent and each room will be its own agent and every collection of rooms with have a controlling agent that it has to pass it outputs though to ensure consistence