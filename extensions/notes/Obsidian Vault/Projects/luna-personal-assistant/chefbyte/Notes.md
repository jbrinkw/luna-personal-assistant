---
note_project_id: chefbyte
---

9/2/25
im gonna cry but it needs to be done. im moving to grocy and throwing away all my old code. this should make this way more user friendly but its gonna be annoyting to agentify this. i mean maybe not most of the issue with chefbyte original was making the root code work not the agent tools. itll just be a lot of thinkng. the primary thing i need to figure out to get this off the ground is how to handle the base items. like any item new item is going to have to be typed. what does a new item need? name, qutity unit type, walmart link, quanity bought, expireation, barcode... that that problay everything. ig the only thing that would natually be linked to a barcode would be the quitity unit type like bag, or jar..

basic tools to add 
crud for
- inventory 
- shopping list
- recipes
- meal plan
- taste profile*

other
- get instock meals
- generate meal suggestion(intent)
- generate new meal ideas (intent)
- generate shopping list(time period of meal plan)

later
- walmart ordering

8/28/25
I definalty want to move in the direction of using outisde apps to help take the load off my devopment. grocy looks good probaly doesnt everyting that i would really want to outsource for this. i can store invnetory. mangage via multip paths including bar code so should be able to handle all of inventory crud well enough. it also has a sectoin for recipies which looks good it list all ingredients and cacualtes what can be made atm. idk why i didnt start with this. it would have been a lot easier to build around this from the beggining... anyways

8/13/25
what do i want to have on the homepage?
- instock meal suggestion. can type an intent or leave blank to get something random
	- maybe it can add tags to each meal for breakfast lunch and dinner and keep a random list of meals on the homepage that match the time of day
- inventory crud? maybe just an agent thing
- food expireing soon
- macro progress once i get that far

7/29/25

ok things to do before week finish with the toolificatoin refactor of chefbyte.

- refactor how the dailey planner is created from pre creating the entire year to just making days we use and then any query of it will require a date range or defualt to the past 7 days
- confirm each layer of meal planner is working
- confirm each layer of the meal ideation is working

  

push taste profile doesnt work. myabe seperate into a tool for like dislike and general to more easily handle mutations

  

maybe seperate saved meals and instock meals into sperate tools or at least in the return of the tool call

  

should set up my tests to use the same sample db to i can push, pull then see the the update went through and then use an llm to judge. also for db io test dont give the ai access to the chats from update when it is checking for it

