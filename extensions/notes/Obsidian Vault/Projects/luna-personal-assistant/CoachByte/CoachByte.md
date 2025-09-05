---
project_root: true
project_id: coachbyte
project_parent: Luna
status: active
---
[[Projects/luna-personal-assistant/CoachByte/notes|notes]]

Planned Features  
graph of gains overtime

  

  

Primary features:

- recording training progress
- creating workout plans dynamically
- work with chefbyte to create a meal plan that matches
- display current workout progress on display in the gym along with wait times

Database

- Dailey exercise tables
- Main goal
- Daily Log
- Weekly Log

  

  

Levels

1: Bare min

- Ability to record and access logs in structured format
    - There will be a structured output for the AI to crate a log for a each type of workout in a day like for most weight based workouts there would be a table with the name like bench press and then 2 columns for reps and weight planned, reps completed and time
- Create a training plan based on the users current progression and/or personal preference that day
- full crud of logs

2: Basic Interface

- Either home assistant dashboard with webapp that displays the CoachByte dash. for the now the dash will just display the day’s exersizes with buttons to mark each one complete

  

  

  

Every day at the end of the day the AI will create a summary of the workouts compelted and progess and any other relevent notes. At the end of the week this will be summerized into a weekly summery. the ai will get the past x days and the past x weeks as context when planning workouts
