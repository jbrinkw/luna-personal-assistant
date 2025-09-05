---
project_root: true
project_id: universal-architecture
project_parent: Luna
status: active
---

[[Projects/luna-personal-assistant/Universal Architecture/Notes|Notes]]

An important part of making a lightweight but reliable universal AI is going to be semantic caching so the prompt size can be kept low while maintaining the agents awareness. There needs to be a system for detecting changes in the agents global context and then summerizing it so it can be included in the system prompt I feel like I’m also going to have to makes strucutre for how to make the context in the system prompt and have mutiples levels of detail for everything

  

background prompt opitmizer that runs failed responses with diffrent prompt untill it works

  

Things to include in the context

- todo list
- shopping list
- personal summary: basic stuff about me, current situation in life, goals etc
- graph of tool / data heirachacy with descriptions
- custom instrutions for how to respond

  

Pieces to the framework

- advanced context management
- flow graphs of common tasks and of tool / data heiarchachy
- multi step processing of each prompt for speed and reliablity
- pre made forms for the ai to fill out to direct its thinking
- ability to spin off theads of works to complete asynchoncously
- custom loras i can attach to the model for each large domain like one for my personal jouranal , work journal other stuff…

  

  

**UI**

I want this UI to be future proof

General laywill: All domains listed in a row on the top of the screen. a domain will have all its pages along the left sidebar.

homepage: figure out some way to pin things from various domain to the homepage. could probaly have an agent for that.

universal agent can be a pull out form the right like in coach byte

  

**Vision**

have an interface where i can interact with all of my domains and the universal agent. universal agent accessible via voice.

coachbyte: have an agent/ interface to keep track of my training progress and handle settting new goals

chefbyte: take the thinking and overhead out of planning means and managing inventory. gives me ideas for what to eat. comes up with new meal ideas and automatically orders food

general byte: catch all personal assistant. keep track of my personal profile, todo items, sends me notifications, manage my personal notes, sets internal reminders that call the ai in the background to check somehting and send a message to the user if nessacery. manages all daily news reports

professorbyte: a reaserach assitant that keeps track of all my projects and what im currently working on to help me track progess. also does research in the background to present daily news reports

  

Universal tables

- notificaitons to user
- daily report
