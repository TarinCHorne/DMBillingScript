How to use the Billing Script

1. Configure the Billing.py
#Note in the future I'll have a config.ini file for this

Open Billing.py with either Notepad or Notepad++ (https://notepad-plus-plus.org/)

At the top of the file there are settings that can be edited
GAME_COST: For adjusting the game costs edit 
STOP_GAP: For forcing an manual bill after a bill occurs more than an amount edit 
IS_PAY_AHEAD: if set to true, will pay into the future, if false will stop at current date (note setting to false may have some bugs, feel free to DM me)

GAME_NAME_MAPPING and GAME_FREQUENCY will need to be setup with any current games
Examples of the formatting of these maps are as follows using Ann as an example

GAME_NAME_MAPPING: is a map of the DMs first name (or any no spaced word) and a 1-2 letter day of the week abbreviation (longer abbreviations would work or full weekday names would work as well) 
mapped to a descriptive name of that game
GAME_FREQUENCY: This is set only if any games are played biweekly or monthly, or every 3rd week, ect.
if no games have an off frequency, this can be set to an empty map: GAME_FREQUENCY={}

GAME_NAME_MAPPING = {
    "Ann M"     :"Ann's Monday Game",
    "Ann Tu"    :"Ann's Tuesday Game",
    "Ann W"     :"Ann's Wednesday Game",
    "Ann Th"    :"Ann's Thursday Game",
    "Ann F"     :"Ann's Friday Game",
    "Ann Sa"    :"Ann's Saturday Game",
    "Ann Su"    :"Ann's Sunday Game"
}

GAME_FREQUENCY = {
    "Ann F" : {
        "Frequency": 2,
        "Offset": 0
    },
    "Ann Su" : {
        "Frequency": 3,
        "Offset": 2
    }
}

2. Setup the initial Billing Sheet.csv
This can be done with Notepad or Notepad++ but it IS NOT RECOMENDED
MS Office or free alternative LibraOffice (https://www.libreoffice.org/) IS RECOMENDED

Customer data can be fit under each of the headers

Player: Whatever name the player goes by

Email: What the Player's PayPal email is

Bill Y/N: Weather this customer should be billed, 'Y' bills the customer, 'N' skips the customer

Pay period M/W/B: weither the customer pays monthly 'M', weekly 'W', or every other week 'B' 

GM/day of week: this will be a comma separated list of GAME_NAME_MAPPING keys that the player plays in, i.e | Ann M,Ann Tu,Ann F | ect.
note that multiple of the same key name will charge the customer multiple times for that game

Prepaid Credits: this is a modifier to reduce the games that a customer pays for

Last Bill Sent: this is a Month-Day-Year date of ware the script will pick up to calculate from
This will need to be set to start billing a customer, set this one day behind the customer's first billed date

3. Reference the /manual_billing dir
Once the PayPal integration is fully setup, only the bills that require manual billing will populate in the /manual_billing dir
Currently all bills that need invoices will be easily referenceable in this generated dir
