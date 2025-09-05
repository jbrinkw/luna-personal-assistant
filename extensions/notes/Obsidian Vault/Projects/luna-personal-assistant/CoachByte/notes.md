---
note_project_id: coachbyte
---

8/21/25
idk how to do the realitive precents. like its easy if im using 1rm but im never really gonna be maxing out.  the only think i can think of is an offset to assume ill always have 2 left in the tank but i dont think thats relibable

7/11/25

I have a basic ui and I actually really like it. I just need to add some finishing touches and I’ll have the full v1. I think the only thing i have left to do is create the tables for the general workout prefrences and something to store current prs for each workout at each rep. then probaly a tool for planning that automatically inlcudes all of the context for making the days workout plan

7/9/25

ok so i have the basics. a ui decect looking ui and an agent that can interact with it. Im not super sure what i need next f… so im going make a chat side bar that syncs the message history in the sql db and stores the last x number of messages. it can sync realtime like the workout data so if i speak to it over anouter interface it will show up in the website

  

7/6/25:

So I have a basic bot with basic tools and a basic interface. is this all I need to get started? I need to think though how I would actually use this. The orignal features I was thinking of was planning workouts and then display them on the wall with the timer. I dont really need to have the audible ding to start i can just create a timer in the UI. for now i will problay be relying on the ui for now until i get a good feel for how i want this to work and then i can build the voice feature on top of it. year for now im not even going to try to do voice. so if we are going full ui i need to add a basic chat interface probaly as a side bar i can pull out and put away. ok so were going to expland the current ui with a persistant sidebar with a chat interface. there will be a main tab for the current day which will display the planned workouts and completed workouts. completed workouts will populate alongside the planned workouts as you go. ill probaly put the time at the top of the presistant sidebar with the chat interface. the timer will start for the specified amount of time when the user logs a set. is there anything else i need to start?

how do i want to display the panned and completed set. rn i have 2 seperate table but that takes up a bunch of space and shows a lot of redundent info. I think a better way to do this would be to have a single list that will initially show all the panned sets and it will just highlight stuff as you do it. Thats pretty simple but then i need to figure out how i want handle devations from the plan. so baseline you would just click a button and it would check off the next planned set from the list then there are two senerios from there the user overwrite part of the next set in the queue like weight or reps or they insert a new workout. I think ill add handeling for new sets later rn im just going to have an overwrite.

  

