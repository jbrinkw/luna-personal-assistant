---
note_project_id: professorbyte
---

8/12/25
how do i want the obisidian mcp server to work. i think im going to have one tool for pulling the schmema and anouter for retriveing a page. simple enough idk what else i could need. how do i want the schema to work. maybe i can just do that and then have the ai make the project summary for me. maybe even a tool to update it

8/11/25
maybe instead of primarily interacting with the todo list via the ui i can do it in my notes and have a background script manage it. like if i had a todo list for each project and then whenever i check something off it goes into the note for the day. then what would i need the ui for? I think it would still be nice to have a ui to have all my todos in one space. also the news agent. 

So i think im going to put the todo list into obsidian and automated: completed todo items moving to the daily note for that project, schedule the moving of completed items for while im asleep. can link todo item status between the parent and child project. the only thing i can think to use the ui for would be the reserach assistant and maybe a summary of what i did the last few days and what i have to do today

how is this reserach agent going to work? theres not going to be anyway to filter what the serach query returns beside setting a date so i im going to need to filter what i returns. also i dont think it would be easy to get a feed of stuff that stuff what that i want to to hear which kinda puts wrench in the idea of making a podcast because i think it would be hard to make one that im not going to be skipping through half of. maybe i should focus the agent to be less of an artical summary maker and more of daily summary. so im thinking i just return a list of article titles to an agent that can see an outline from the past week of summarys and it will look through the article list for anyting to look into more and produce a daily update. i dont think it would be that long usually

the news agent is going to be more complicated than i originally planned im going to push it to after i get my first realse to devop. so that leave the professor byte ui is there anything else i want to do beside the todo stuff? I also wanted an agent to summerize recent progess and tell me what to work on next. do that later.

i think the part of the agent that make a report of possivbe tools and techonoifies that could help with the project would be an easier start bc then i can make an initial list and it would be easy to groud future souces off that bc i can continue to run the same initial seach and see if anything new comes back and also look for update and the exsisting tools that could apply i think that was myinital idea and i like that a lot more than jsut a news agent. whatevef.. lets do that first

8/8/25
how do i want the agent to interact with the notes? what is the point of the notes. i want the agent to be able to help me with projects. im not going to have so many notes it wont fit into conext so i dont see why i would even need to compress it. i should give it the initial and it set up the inital project desction and summary and todo items and roadmap then every night i can process the diffs and update stuff so i just need to make a tool for accessing the root of each project and all the docs

7/27/25

I’m trying to figure out what features to implement into this to help me focus and stay on track with work. I think my biggest problem with work is I’ll pick up a bunch of momentum and then I’ll hit a roadblock and spin out and then it’s impossible to get going again. So in thery if I had something that I could at least talk to and maybe even track me to help me out of whatever rut by either talking me through it or suggesting something else to do like a break or work on anouter project. Just making a bot to talk to would only really require rethinking where I keep my notes probaly moving to onenote or something simular and then giving the agent read and write access. That would be a decent level one. From there I think the next best feature to add would be a todo list with tags. Tags could be for ugency or to link to a project. The biggest thing I think this could help with is not fogetting about stuff and not letting myself get sidetracked and break focus. Like if i wanna check my va shit it would be better to add that to my todo list than check it while im in the middle of working on something. At somepoint I think it could help to figure out how to implment monitoring to watch for when I get stuck and i dont realize im spending too much time on a problem. That value to effort isn’t quite as good tho so its definatly a later problem. Just right first two things would probaly be a great help and keep me on track as well as help me live healther. I would actaully probaly be pretty easy to do basic monitoring like just recording what app is active on my computer and io activity could probaly make a desently accureate log of my daily activities with that and use it to remind me to take breaks n shit.

  

todo list i can add stuff too instead of sidetracking myself but gets it off my mind

  

  

8/7/2025

so of these features revolve around managing my project notes and progress and helping me find better ways to do stuff. so the primary db will be whatever note application i use. then there will need to be a table with an ai summary active project. im thinking that each project will have its own db and there will be anouter table to track active projects. jira? nah i dont need that much complexity. each project is just gonna be a name, description, todo items and note db. then the project main page will show all active projects and major todo items. then you can click on it to see and edit the description and goals and then a link to the notes. then there can be anouter page for the news agent where you can see all of the report and edit the manual tracked things along with the automatically tracked item that a decied by an agent looking through my projects

