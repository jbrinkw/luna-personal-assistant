---
note_project_id: universal-architecture
---

8/8/25
Remember I am building a univeral personal assistant so my goal is to be able to upload and tool file or mcp server and have it automatically implemented and organized into the system. what else would I have to add on top of the tools and the desriptions? General domain description. Should probaly have a database readme the agent can access. shouldnt be to hard to add an entry into the ui hub if i stick with the iframe apporach. OK. let just focus on the tool import and organizatoin of tools
how tf do i want to set up this agent system.

8/12/25 so if i want to go with the obious core / extension setup  i need to figure out a format for extenstions to interface the hub with. the way the tools are documented might change but for now the defualt mcp server should be fine. if they have a ui then ill just need the link, run cmd and maybe basic docs for it. then just he mcp server but at the very least to tools with have to have the hieractacal naming. yeah its really not that complicated. i mean eventrually im going to need to add some extra doc reqs for the mono agent and then probaby refactor how the tool servers work do i can attach the linker tags. once i start working on the linker agent ill probably need detailed doc for each project. linker modules 

8/7/25

i dont think the seperation of domains just by naming like im doing right now will work in the future i think the ideal approch will end up being something like my chefbyte demo where the main agent just has an idea of the whole shemea and a tool and then routes it to a sub agent for each domain

8/4/25

So i’m ready to get started on level 1 of this project which i have decied will just be an mcp manager that can take a number of mcp servers and wrap them into one mcp server with new tool desctiption and an endpoint to pull a graph with the tool graph. well step one is just making an tool manager simular to the other one. how do i want to do this. maybe just a script that will read from all the mcp server and generate a new mcp server script

lets think about the next level of this so i dont waste my time. so end goal is the cs killer. luna is just a good way to build towards that. the cs killer and luna are tageted towards differnt things so i nee do figure out where to drawl the line. cs killer is made handle multi step repeditive processes of whatever lenght in a reliable way. luna just need to be able to understand a large set of tool and be able to pick the right one. so with luna i just need to focus on the agents ability to understand and reliably interact with large toolsets and create plan for parrell multi step proceses.

for the the tool router part i just need to make the mcp wrapper, a tool that can write the expanation graph to be included in the system prompt

is there any reason i wouldnt just want to use the exsisting tool descriptions? i dont think so but i could potentially need to use an llm call to create the orginazation graph for when there are nested layers. theres also to orginaztion into push, pull and action groups. do i want to require the root mcp server to name and organize the tools. i think it would be easier if i did named the basic 3. idk what else i would need. db io and action tools covers everything. in that case i wouldnt need to make an llm call to organized stuff bc i could just use the name

so i dont think im gonna need an llm call to orgainize off the bat. i can just use a naming format inthe orginal mcp server and the server can read that and create the graph based on it. i should present the graph in a readable way like mabybe json. after i get the basic stuff working on the multi processsing. I want to create a small template for the ai to respond with starting with extracting each individual task and then thinking about the tools that would it would require…. think a detailed step by step process to force the ai to think in small steps

7/30/25

I’m almost done getting the chefbyte and coach byte read so i need to start thinking about how im going to intergrate them. i have 2 primary ideas plug in the tools directly with shema based naming and no description in the tool names and then attach a manually made schema graph to guide the agent in how to call the tool. i think it could potentially help in clarity to have a custom tool processor along with the custom tool schema but i dont think that will be nessacery intialialy. so all i need to do initially is attach both mcp servers. make sure the naming is good. and bulid the schema graph and then expirement with the tests to see how well it works? what else the initial version of the project shouldnt be that hard. i think the idea i had initialilly was to apply graphs to every part of the agent. maybe i should log all my interactoins and then have the ai look for graphs that it can extract from that but there probaly wont be any graphs to take from a personal assistant that more of a customer service agent thing

  

