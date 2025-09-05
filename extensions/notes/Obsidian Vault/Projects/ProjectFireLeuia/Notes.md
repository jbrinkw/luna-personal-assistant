  

7/24/25

I think I was on a good path yesterday with making graphs to ground the agent in something proven. I really cant imagine a commersal product working any other way bc nothing else will provide anywhere near the reliblity and compliant. at some point i feel like most apps will release with a graph for ai’s to naviate with them. its not really that complicated of a concept. i mean currently a lot of them are releaseing with mcp server but i dont think they have any internal orginization i mean it shouldnt be that hard to make an mcp wrapper with orgainization

I think i got a little caught up trying to set up web arena. that might be ahead of what im doing rn. remember my plan rn is to design a comlete system reguarless of current tech and figure out a way i can contribute. the main innovations that are required for my system is modular memory and agents that create DAGs of UIs and processes. modular memory is more than likey going to be far over my head to make any progess on but i could realistically make the DAG agent.

  

7/23/25 out for customer service blood

Is it just me, or is everyone constantly getting fucked by paper pushers who can’t do their job? My dream of replacing all of them has never been higher. What would it take to create an AI to replace them? I think it would just be something capable of automatically organizing tools and processes, and an agent capable of navigating UIs. For something to be applicable to all businesses, it would need an easy interface and include a tool, flow, and agent manager. I don’t think any version of RAG will be truly scalable. There will need to be some system for caching or learning the workflows.

I guess there are two ways this can work: either fine-tuning on all the tools, flows, agents, and docs. I don’t think that would be ideal though, because you don’t want to fine-tune a monolithic AI with all the company’s tools—that will open them up to jailbreaking. However it works, it will need to be fully segmented by agent. That doesn’t rule out fine-tuning, so the two options are: importing primary knowledge into the agent via fine-tuning, or having a purpose-built agent that works through the knowledge base and creates graphs to guide the flow of work. I can’t imagine anything else becoming popular. Building the knowledge/process graphs grounds the AI in something that can be easily verified. This system needs to be designed from the ground up to be reliable and auditable. I don’t think current systems would have too much trouble following a well-built graph without fine-tuning, so that leaves the main challenge as creating an AI that can build a graph of arbitrary scale.

Humans learn in multiple passes: first listening, then we process and ingest, and then apply and relearn anything that was missed. I think I should model this AI system on the same process. I’m not sure the AI would need ingestion time. There are two ways this can work: a fast listener agent that just observes and takes notes, then passes off its data to a slower, smarter model that takes time to carefully build out the process graphs; or the process graphs could be generated in parallel so the teacher can correct errors as they come up. I don’t think AI is smart enough at the moment to make that work on an arbitrary scale. Maybe it could be worth trying as a preview, but I just have a vibe that will present reliability issues. So I imagine v1 working with a listener model that works alongside the teacher, asking questions and taking notes, and then the organizer model that takes its time to relisten to the recordings and examine the listener agent’s notes to build out the process graphs.

So on top of having do develop an agent that can create process graphs I imagine that this system also require some way of modularly storing memories and including them simular to how loras work currently. I don't trust standard rag becuase it will never be as relialble as a model that actaully has interinalized the company knolege. standard rag will still have its place but I definantly need a way of internalizeing the data into a model for a commericail ready product

I think fine-tuning will ultimately be required because there will be agents that are going to require more proprietary info than will reliably fit into the context window. Maybe LoRAs could provide a solution to this. I just need a good way of internalizing data into the model and not just RAG, because that’s not reliable enough. Ideally, I would be able to create knowledge stores that I can include in any amount with any LLM call in a way where the data is as reliable as if it were trained on it. Then, on top of that, I’ll probably have it ground all of its decisions in its knowledge foundation for increased reliability and logging.

To summarize what I have so far: an AI UI for managing process flows, tools, agents, and knowledge blocks. A human will teach a listener AI that will record what it’s shown and ask clarifying questions along the way, and that data will be sent to an organizer AI which will create process graphs that the user-facing AI can ground itself in. Some kind of fine-tuning will be required to internalize company data, and ideally it can be segmented and attached to LLMs in any way.

my method seems to deviate a bit from the current norm in that there is a listener agent and the process graph builder agent. there are some really good benchmark envs but they seem to be driven by text prompts. I dont think i really considered this becuase it dont imagine an agent system being complient without first being taught by a human and creating the process graphs. is there any value to expirmenting with those benchmarks. i mean if i got something working well on that i could definatly set a founcation for the main project and maybe i can find some tasks where i can teach the proces graph agent.

I imagine the process graph exututor agent would follow the graph excusively and call in a human agent when there is a devation and there could be a dashboard to track devations and they could be sent ot the process graph builder agent to automatically update the process graph

ok so i found some benchmarks/datasets that actually fit my idea so i can move forward with that. i think i should do the basic non learn agent first tho just to get familar with the setup and the gui interation

current todo:

-setup demo env

-study peft

-study current sota for agentic systems

  

so i think a good first step for the innovative part of this project would be creating a graph of how a gui works. i think on top of the process graphs is going to be important to have a master layout graph for each app as it will add an extra layer to auditing and compliance as well as allowing the ai to forge its own path when figuring out how to do something if the user allows for it.