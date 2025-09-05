Project Summary:

keep stock of all food items and provide personalized recipe suggestions and build shopping lists. primary interaction will be through a fire tablet on fridge.

  

TODO: make it flowy and dynamic like you are talking to a person

- create focuses and flows including validation checks
- classify the scipt
- make a better test script
- structure the learn prefrences into like and dislikes and general
- make sure convo history is included in the prompt
- return 10 planned meals by defualt

  

planned meals

shopping

saved recipes

  

definitions:

- dynamic modification requests: this means that the user should able to make a request with arbitrary structure like they should be able to say “add chesse remove the milk and add some ground beef to my shopping list” “it is the goal of the app to be able to figure out what the user means and translate that in to the requested change
- return whole object with function: this is when a user asks about the whole contents of something or doesnt ask about one thing specifically. for example if the user say “what food do i have in stock” the ai should call the funciton to return to print the inventory.
- answer specific questions with natural language: the user can ask specfic questions like “what do i have that is going to expire soon” “how many potatoes do i have in stock” “do i have the ingredients to make grilled chesse” “estimate how many days the food in my shopping list will last me”
- custom instructions: this are built for each function and feature. they tell the ai exactly how to handle the request

general focus

- inventory focus
    - custom instructions
    - dynamic modification requests
    - return whole object with function
    - answer specific questions with natural language
- shopping list focus
    - custom instructions
    - dynamic modification requests
    - return whole object with function
    - answer specific questions with natural language
- planned meals
    - custom instructions
    - user asks for a meal ideas
        - 1: internally list the number of ideas that they ask for or 5 if they don’t specify. each idea should include the name of the meal and the ingrediantes required
        - 2: check that each recipe if all requirements arn’t met return to step one
            - can be made with the current inventory if the user specified that
            - does it match the taste profile and learned prefrences
            - does match the specific request of the user like did they ask for high protein or easy 5 minute snack.
        - 3: list each meal idea for the user to see. the list of meals should be followed by this prompt to the user “do you want to add any of these to your planned meals or generate more ideas”
        - 4: from here the user can ask for more ideas in which case return to step one. if the user asks for a new set of ideas maintain the number scheme so if the first set is 1-5 the next should be 6-10 then the user should be able to add meals from both sets when they decide they want to add something to planned meals. if the user wants to add something they can respond in whatever way they want meaning they can say “add the first 3 to my planned meals or “save 1,3, 6, and 8”
        - 5: if the user didn’t restrict the ideas to the current invnetory ask if they want to add all the required ingrediants for the planned meals they just added that they dont already have in stock
            - make sur

i want to convert this project to have flows

  

9/24 cmd refresh

structure: will work like a basic chat interface where you talk normally to the model without and special characters and can also run special functoins like /list inventory or taste profie and also the cmd to update taste profile etc. still can make the alexa inergration and app for scanning in items

  

9/29

fix flow like if i asked for new recipes and dont chose any of them it should say updated shoppping list. it should also ask to update the shopping list. i should make a more defined flow for the ai to follow. like have it see what the user is asking then list all relvent info so it doesnt get overwhlemed. i also should add checking to see if the suggesttion or response makes sense

i should make different focuses and flows, like inventory modification and recipe suggestion and have validation checks

  

Validatiion checks

recipe suggestion: accuracy vs taste profile | does it include items not instock when the user didnt ask for that. if the user asks for new stuff are any the suggestion already in the taste profile

  

mai

  

  

Technical:

- frontend docker is an html webapp
- backend docker is flask and python
- database docker is postgres

  

  

Features:

Core:

- record food inventory
- store a history of food preference and liked recipe
- generate shopping list

  

Extra:

- scan items in/out with barcode, picture, and voice
- import items from walmart order
- automaticly build walmart orders
- find online recipes instead of creating them

  

Food Import Process

Walmart import: There will be an automatic import from walmart whenever i order something. After the import is comple a noteification will pop up on the tablet that there is a new order and it will let you scroll through the new items and add expiration dates either manually or through ocr

  

There will be 2 buttons for adding and removing which will give you the option to search or scan barcode

  

Project Breakdown:

  

Log:

6/13/24

I got the start of a working prototype with flask and docker but getting the database to interact with the wordpress along with the work of making that all pretty n shit is not going to be be worth the effort. what i can to i rethink the primary interaction method and use an easier platform to build the visual part like gradio or streamlit or something else ill do some research. I dont want to be a web devopler and i was spending too much time on it. So instead of using barcode i think im going to start out with voice and ai image analysis for CRUD. It should be pretty easy to have an llm do crud for a database and its not even that bad of a way to interact. Tonight i think i just want to do a proof of concept with adding in stuff via image and copy paste walmart order. also in the future i think i may try to use that app as a backend for what im doing bc they already have a lot of the features that i want but dont want to code.

6/20/24

I used steamlit and it is finally coming together i have a decent first prototype with a screen for managing the inventory and getting recipes. This is what i want to change

- test and refine the prompting for the inventory management
- redesign the recipe suggestion page probably stack the prompt box and inventory table vertically and have the output on the side so it has more room
- add the ability for it to create shopping list on the inventory page
- add needed item from a recipe to the shopping list automatically
- save favorite recipes
- change the suggestion chat box to a dialoge
- recipe book
- make taste profile box go away after its saved
- add a button to show taste profile after its loaded
- add a text box to show a short summary of the taste profile. use gpt4o to write a short 50ish word summary and display

  

6/22/24

This is starting to get to be a headache. I like streamlit but it doesn’t really integrate into my Wordpress the way I want. maybe I can get it to integrate a little better buy I probably shouldn’t even really worry about that for now. i kinda want to put it into my ec2 to just fuck around with so I don't really have to worry about conflicting with my website and that also free anyways so whatever. then I can experiment more with flask and how to get this to dynamically update I feel like I should do a little more looking to see if streamlit is really want I want to move forward with but I also need to spend a decent amount of time just thinking about how i am going to try to make all of this work and what i want to do in the future so i know what I'm future proofing for. honestly i don't think its really even worth trying to integrate into my Wordpress yet. I should probably just optimize for my use and then see how to transition it later. hopefully streamlit and flask are all i really need maybe luna can help me work through all the parts of this project and how they are going to work and then she can summarize it and check that what I'm trying to do is possible.

  

i need help maping out a project that I am working on. im going to tell you everything I've done so far and what im thinking about doing then we can start a dialog to fill in any gaps. i want to start with the conceptual idea of the project, what I've done so far and then what I plan to do later. after that we are going to explore how exactly to build off what I've done so far if I need to change anything and how im going to implement my future feature.

I am trying to make an llm powered inventory management / recipe suggestion app. I bought a fire tablet that i am going to put on my fridge that will be able to display and interact with the inventory and have another page dedicated to generating recipes and meal plans based of the users tastes and current food inventory. For example i want to be able to ask what is a quick 5 minute meal i can make with what i have right now or generate a meal plan for the week and add everything i don't already have into a shopping list. also at some point i want it to automatically create walmart orders based on my shopping list. This is a basic overview there is more depth that i want to go into.

  

So far I have a streamlit app with 2 pages. The first page has 2 inputs. One text box where the user can type in a command that get evaluated by an llm for how to change the inventory. the other is a image input where the user can add a screenshot or receipt that will get imported into the inventory. then on the other side of the screen is a basic table to show the inventory. on the other screen is the recipe suggestion stuff. there is a prompt box for the user to request whatever kinda recipe they want like “a quick 5 minute snack” and a check box under it to restrict the suggestion to the current inventory or not. under that is the current inventory table and to the right is the space for the output recipe. for the db I'm using postgres. i have the streamlit and the postgres server in separate dockers.

  

This is the part where I'm starting to get lost. So right now I'm trying to make an alexa skill. to interact with my streamlit app like an API. I want to have the alexa skill setup so I can say “alexa tell chefbyte” and it will send the rest of the command to an llm which will evaluate if I'm asking for an inventory change or recipe suggestion. I'm also not sure how I'm going to get that to go from the alexa skill to automatically updating on the fire table that has the streamlit app open.

  

7/10/24

Major progress i combined mulitple pages into one chat dialoge interface. i might make anouther page for saved recipes but that is for later

easy stuff:

- sidebar refresh looks bad
- taste profile save button should close the text box
- readd picture import into side bar
- modify sys prompt to ensure if i include an expireation date for something it is always a new item
- sort inventory so expiration date suff is at the top