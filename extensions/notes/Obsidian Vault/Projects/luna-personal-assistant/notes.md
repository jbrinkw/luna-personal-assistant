---
note_project_id: Luna
---
9/20/25

## Summary

The Luna project is progressing towards its first release. Work has begun on the Grocy import wizard, including the implementation of AI-powered field generation to streamline the import process. The project summary and action items have been established, providing a clear roadmap for development. The primary focus for the upcoming milestone is the creation of a comprehensive user guide, which will be essential for onboarding and supporting users in the initial release.
9/10/25
ok it is crunch time i gotta lock in. i need to finish the docs, get basic gorcy import done, and hopefully get a local voice agent done or at least set up calling bc that would be a great demo then also the dynamic memory feature. 

im gonna stick with gpt realtime for now just for the demo bc itll be easier
9/9/25
the biggest thing between me and release 1 right now is good docs. i need to make docs for the the doc and all the extentions and each of the diffrent strageies for speeding things up. i think if im going to have multiple speed up strategys im going to need to make a tool manager to toggle all of the settings. that can be a later problem tho. so rn i just need to make docs for for the core and the starting extensions. 

how do i want to setup the docs?
project summary
user guide
core:
- agent setup
- tool setup
- agents:
	- basic 3 layer
	- ... other agents
- agent helpers
	- light schema

ok so i finish the basic testing system and refine the docstring structure a bit and started working on the documentation system. im definaly gonna move it into the same repo tath makes a lot more sense for ai coding. next steps are just finsish the docs and make the code more presentable and then ill pretty much be good for first release. after that i want to get right to figureing out how to make stuff faster again and also figureing out the dynamic memory system so i can have natual coversations with my notes. i also dont really imagene myself using gpt-realtime long term bc i wan to have long conversations so im probaly gonna need to setup something local. all of that plus getting grocy intergrated and ill be in a greate place for applying for jobs and starting to market

honestly my main goal for tmr is just to get the basic docs and cleaning done and then figuure out the chat with notes and then maybe a local voice agent bc ive been dying to be able to chat with my projects

9/8/25
give tools a flag to be async with 2 types. confirmed will run in background and return confirmation message. then a types for unconfirmed async which will generate an llm call in the background to confirm that the tool call was sucesssful and only return a confirmation to the chat if there way an error. 

Run the router and domain functions all at the same time so by the time that router has completed
9/6/25
For queries that require a thought, set up the thinking  model to essentially think out loud by returning regular updates on its process to the voice model

An important feature for the note agent would be collaboratively expanding details on the future roadmap for example with professor bite, it would start with a general explanation of the intent of the project, and then the side-by-side with the note agent the user could conceptually build out their project into more and more detail

If I want to have a intellectual conversation about the future of work after the singularity I should be able to ask it to do deep research with the focus of generating a knowledgbase of the subject that I can then directly load into the context to give it a stronger foundation in the conversation 

9/5/25
I'm trying to figure out how to speed stuff up be right now were looking at at least 3 seconds with the 3 layer router, tools and synth strucutre with 4.1 mini which is mostly reliable and 2 second with gemini flash lite which is alright buti wouldnt use in production as is. 4.1 has acceptable time for just the domain layer if it only calls 1 tool but its ttft adds up really fast 4.1-mini. maybe that extra timeis just the react agent it seems like the 4.1 family has decent speed

I’ve decided that GPT real time has enough context window that I can dynamically load in context such as project notes so I can chat seamlessly to ask questions that should handle most of my interactions, but the voice model isn’t going to do any serious thinking so I need to have a toolthat will reflect on the query asynchronously and and get back to me 

Should have a tool to turn up the intelligence of different layers in the model for when I have more complex queries
Tool result pass through will help with latency quite a bit

Document all workflows

Set up a space in the database for pending messages from a sink tools

And the automation layer I should be able to define context groups like notes and to do’s for a project or personal notes then the load context tool can load that in and unload it dynamically

Have tools that trigger agents of very intelligence that have full access to the tools of the whole project so I can ask her to look through my notes and think about something or go to My to get hub and stuff like that. I can ask the model to think and it’ll ask me what level of intelligence and then I’ll go about it.



9/1/25
There a lot to do. I fixed the wierd latency issue appartely it was the mcp server no clue why that was so slow but local tools work great. i dont think im going to try the cut down model statck without  a router yet i need to get with a router working reliably. its gonna be a pain in the ass to go through all the tests and figure out why each one is failing. i think the best way to start is be rewriting the test to tell the agent exactly what to do and then once i got that down we can do progressively more ambigous. thats definaly a good place to start like use the exact tool names. after i get that i need to impolmetn all the other tools i made for todo list and obisian and then theres also the whole reseach agent piece i havent done yet. i havent enen really figure out how i want to impolnet that yet. i also need to implnet a memory system so the ai can remeber the ways i interact with the tools. fuck theres kinda a lot to do.
i need to transistion to grocy. thats gonna be a pain in the ass

8/29/25
its time to refactor the agent to make to replace the slow ass open ai models and add some reliablity. for speed we are going to switch to gemini flash lite which is exponetiallly faster like every open ai model and also free? anywasys for relibality. im going to flip the previous struture so now each domian is going to get the user requrest in parrelly and it will do its own processing if there is any which will then go to the output agent which will look over everything combine the responces and check if there is any follow up stuff like if the users requrest requresed the interactoin of multiple domains it can repormpt the system for now i think ill just have it look and the ask the suer if it wants to reprompt. ye thats about it. 

8/14/25
phase 2. i need to rethink how i do ai coding. i need to put in the work to make extensive tests and set up that whole system to make it easier for the ai to fix its own problems. like when i give it a task i shold write a very speciic intructions on the goal and define what tests it should pass so it can write both and know when its finished and at the end run the whole repo to make sure everything still works. i think the ai could be a lot more indepdent if it had clear docs, tests and a simple goal. i think on top of that before it does any coding it should create a detailed plan of what to do and i should have to approve it.

now that i think about it there is a lot left to do to make this useful. coachbyte is in a mostly useable state. chef byte needs a lot of work to make it more funcitonal like walmart ording for a start and ig calories arnt need rn. i feel like i need to remake the ingrediant matching system and in general i feel like its gonna need a lot of polish

ok this pretty much works but the agent is fucked langflow is way to slow so i kinda need to refacor that to make this useable

8/13/25
ok the refactor is going well we are almost done. the only thing i need to do besides get the stuff up from before is make the repos for each individual domain and then setup a new workspace. im resitant to call it the first release when the test dont all run but whatever ill do some manual stuff and see if it works good enought. refactoring the agent to multi level active heiarchy is on the to do list. oh and i need to load the data in and make a back up. and fix the proxy to connect to the voice assistant

8/11/25
im getting the first release done tn fuck this. whats left. minor updates to the ui for PB. combine all the UIs and make sure the hub works. then i need to unifiy the db. probaly sql lite ... nah full on my sql server. and then make a seperate db for testing. then i need to start loading in my actually data like setting todo and importing my food inventory, split and such and start using it to move forward and figure out what else i need to do. 

i can imainge once i build this out more that i could make a pretty good looking product ive i made a core luna assistant and then had a repo for each domain and marketed it as extension. i wonder if there is already a personal assistant hub like that

while stuff is loading I wan to think thing about the future of luna. so i definatly like the idea of a core agent take extenstions. they can have a ui or be headless. the core luna only carries the role of running the hub, being able to load up extensions, managing the agents organization graph and running the database. the core will also have UI for managing linker agents which will allow the user to link functions of one agent to anouther like linking coachbyte and chefbyte. how will that work. in that case i would need to 

linker agent ideas
- create meal plan based of todays split: chefbyte would need access to the split, how? i dont want to hardcode access i want to design the agents in away where they can be abitarily modified with natual language. i could rely the monolithic agent by adding linker tags to node that tell the agent to pull some data or check something. maybe initiially it willl be enough just to explain it in the mono agent but i think it would probaly be better to find a way to attach extra instructions to a node


8/10/25
wtf was i working on. i need to finish the ui which means making sure that chefbyte was imported correctly imported and then finishing the ui for professor byte and added the research agent. the main 

8/6/25

this has a lot of potential so keep me on track in life and significantly increase my rate of progress. i need to figure out what my endgame is so i can actually achieve that tho. currently i have a good start but i feel like im missing the iceing to hold everything together. I think the biggest thing that are missing is a unified interface and some general assistant features. like rn i have a bunch of specialist but nothing that really holds all of them togetther. to start i need to bulid out the todo list features and the internal reminders then i need to figure out a away to give the agent a past and present view of me so it knows how to help

the biggest way that luna will impact me is managing todo lists, reminders to do stuff, helping me create and stick to goals (dailey, weekly, monthly) and then the resarch assistant also keep me upto date on news

so i need to finizlize the stuff im working on rn and materialize some of the things bc thats whats really going to make a differenace in my life. i think i shold just get the tool calling reliable and make the unified interaface and then make new tools. i can to the multi step stuff later. i really want to get this new stuff working and start to use luna everyday to help me and learn firsthand how to improve it.

how do i want to seperate general byte and the research assistant? should probaly just seperate it by the notes they mangage. its not really that complicated general will have the day one type notes and the todo list and life plans then research byte will have all the notion notes and lists of of active projects

okk more bs. langfow has decided to stop working consistently. do i want to spend time fixing it or just use something else. bc rn i just using it for a basic agent. yeah so rn i cant think of a reason i cant use just a basic agent with agent sdk. should be less buggy and bs

8/1/25

clock is ticking in need to pick up the pace. i have most of the tools working under the 3 different agent as an mcp server it should be ready to start fucking around with the next level of organizing agent and testing with ambiguious querys. Instead of ambiguious querys i think it would be more effective to just switch the routing model to nano. and get that reliable. i need a better way to run tests tho i spent way to long working on my current tests and they arent exactly reliable. how would i make a standardizable test? it would need to be able to route the prompt thruoug a langgraph endpoint. instead of trying to use a bunch a different shit lets just make a testing agent that can take any langflow endpoint and a structure format for testing. i dont think that should be too hard. ok so how to i standardize the test well there will be 2 types of test.. maybe not 2 types because i want to support abraity lenght in the future. so ill just have test blocks that can be run in parrell. ig i could use test clusters to group under agent so i can have a way to run the reset scripts before running the tests yeah that makes sense i cant imagine a better way to do that. at somepoint i want to figure out a way to automatically make these tests as it will be important to the cskiller. but yeah until then just make a script that can take a langflow endpoint and a lists of tests and make a log an llm can judge

  

7/28/25

do i want to have an mcp server for each push, pull and action or just make an mcp server for each domain and have a wraper to subdivide the tools from there. depends on how the mcp servers are presented to the agent if i want to. i dont think the way the the tools are presented is ideal for a lot of tools. but i dont think there is going to be anouther good way to give the agent access to tools with input validation. is input validatoin that important? i think it gave better results earier with input val. but i feel like a decent model wouldn’t struggle if i custom made the shema and had a standardized format for tool calling. im kinda stuck on the chefbyte app. that has such a large codebase and feature set im a little overwhemled with the idea of documenting and refactoring it. the features along would be a lot to document but how they work would be a big headache and take a lot of time. im going to have to do it at some point tho so might as well do it now. once i get it cleaned up i can just keep it clean and not worry about it for awhile. so to recap my goal with getting chef byte and coach byte ready for the transistion is making sure they are individually working and well documented. i need to manually review the unit tests for both and make sure the documentation works well and then probably have a multi part unit test with ambiguinity so test how well the model handels uncertainty. that will all be very important when im testing the monolithic agent. once i have that done i can start expirimenting with the diffenent structures for the monoligthic agent and not have to worry if my foundation is weak. kudos to the auto ai for pulling that steamlit off, that was imipressive. i think chefbyte and coachbyte are probaly mostly good to go i just need to review their unit tests. but if that works then ill be ready to start architecting the monolithic agent. i mean tbh a lot of the main functionality from chef byte is missing. like the dailiy palner is barely functional from what i remember and i need to refactor how the db works.i also dont think I have a good way of adding the ingrediants from planned meals to the shopping list thats all gonna be a pain in the ass. i imagine all of the getter and setters are working thats simple but the main fucntiality is pretty jank at the moment

  

7/15/25

I need to finalize the chefbyte prototype before I add in the coach byte agent

  

7/13/25

So I have a basic version of the coachbyte setup so now i just need to use and and fix bugs as they pop up. the next big project is going to be finalizing the chefbyte agent cluster and then adding in coach byte and optimizing i already have a decent start with chefbyte i just need to finish that test out

  

6/27/25

making progress I like the transition to the mcp server center architecture. it makes it much easier to refactor the code compared to going into the ui and making edits. now i just need to figure out how to strucute it. I need it to be an agent so the output is going to have to feed into back into the main agent where it can decide to if is done or not so im thinking were going to have the main chat session and then the internal chat session that will get cleared whenever it is used to output to the user. do i want the main agent to pass the whole chat or create tasks to pass to the chefbyte sub agents. i think it would be more future proof to create a list of tasks becuase then the subagents can natually iterate through them and that would also remove the need for internal memeory. maybe not because if something goes wrong then. no unless i am directly passing the output of the subagent its need an internal monololg. well for now i think i can just setup a structured output where the output of all the sub agents just goes striaght into the output angent but in that case it wouldn’t really go though the main agent agent it would just be linear path. thats probably a good way to start i can make an agentic loop later. so for now im just gonna have a main agent that has a general knolege of of all the sub agents and then creates a task list for each of the sub agents or

  

6/24/25

I am a little lost in the bredth of this project. I still trying to figure out exactly how to organize all of this. Like rn im going to have the home assistant agent which isnt to compilicated it can fit in a single agent pretty well. to avoid the slowdown from nested routers I’m thinking about copying the struture that i had in the personal chef from before with seperating into push, pull and tool agents. It is also a decent idea to either use a really smart and slow model and just turn off thinking so we are putting all the work into the first few tokens which should be pretty fast am maybe better than a faster model with time to think. maybe i can give it an output formatt that include a checklist (and flowchart) to figure out which agent to activate

  

6/22/25

ok i go a bunch of stuff into home assitant and i have an agent sdk agent work but ive all but giving up trying to import my HA mcp into autogen studio. I didnt think about before that at least for testing it probaly wouldn’t be that hard to just manually make the tools from the HA mcp server and put it into auto gen studio. I should probaly explore autogen studio and make sure its actually the platform i want to move foward with before i invest time into make autogen studio work

  

6/21/25

I need to figure out how exactly im going to organize all of this. I’ll probaly be running most of the agent backend in a docker, maybe the voice agent stuff in anouter docker. idk ig it will just be a couple docker in proxmox. i dont really know enough about how

  

6/20/25

Ok so I can definatly see myself doing a full intergration with home assistant and setting up a local voice assitant but before I do any of that I need to get the hardware installed and intergrated.

  

6/19/25

Well time to get back on this horse and this time this has to be exponentially more impressive. When I was working on this before I was doing a lot of manual coding and orcastration. I think there is a better way to do this. I need to have a platform like the tool hub that can factictate the intergration of these tools. The only manual coding I should be doing should be developing the tools in a sandbox and then drop them into a tool manger and intergrate them through a UI. The UI also need logging and monitoring.

  

New features:

- UI for intergrating and oganizing tools
- organiztion has an option for active routing with an agent at desicion node or passive with a simple directory structure.
- UI for monitoring and reviewing logs
- Background agent via large slow local models or batch api operations
- UI intergrating whatever model you want
- UI extend logging to track error between differnt models
- continuiously running docker to run multiple python functions at once
- UI python function manager to log an moniter python functions

  

MODULAR AF

  

auto gen is looking like the perfect place to start working on my agents. I’m not sure it has the full customizablility that I’ll need in the future but I think this is a really good place to start and if it doesnt have everything I want i think it will at least be a good foundation to build around. I think the big thing that I’m going to have to build myself is the intergration with my home servers and the scheduled reminders and checks. and then the personal assistant

  

4/7/25

I have a semi functioning rough draft. The routers need to be optimized and the features probaly need a lot of refining. I also need to make a clear map of the dataflow and how to use all of the features. after i create the unit tests for the basic functionality i need to remview the code and cut out all the bs

I’m going to need to implement a database of ingrediants and assositated links. ive been putting it off but i need to figure this out bc its a pretty important feature to the core funtionality. its not that hard to generate

  

