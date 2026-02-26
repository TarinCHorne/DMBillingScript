import requests
import csv
import re
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
import calendar
from enum import Enum
import os
import uuid
import json
import sys

BILLING_FILE_NAME = "Billing Sheet.csv"
LOG_DIR = "logs/"
ERROR_DIR = "manual_billing/"
BACKUP_DIR = "backups/"
GAME_RE = r"(\w+)\s+(\w+)"
DATE_FORMAT = '%m-%d-%Y'
GAME_COST = 20.00
STOP_GAP = 600.00
IS_PAY_AHEAD = True
DEBUG = False

#PP API Config
#PP API Config
ENABLE_PP_API = False
IS_SANDBOX = True
#Sandbox
SANDBOX_MERCHANT_EMAIL = "********"
SANDBOX_CLIENT_ID = "********"
SANDBOX_SECRET = "********"
#Live
LIVE_MERCHANT_EMAIL = "********"
LIVE_CLIENT_ID = "********"
LIVE_SECRET = "********"
PP_TERMS_AND_CONDITIONS = """
Terms and conditions go here.
"""

"""
Hello user of the billing script, here is the map of all the games
the script will generate billing data for.
Make sure to clear out example Ann games and fill in your own with
the same formating (python dictionary structure)
"""
GAME_NAME_MAPPING = {
    "Ann M"     :"Ann's Monday Game",
    "Ann Tu"    :"Ann's Tuesday Game",
    "Ann W"     :"Ann's Wednesday Game",
    "Ann Th"    :"Ann's Thursday Game",
    "Ann F"     :"Ann's Friday Game",
    "Ann Sa"    :"Ann's Saturday Game",
    "Ann Su"    :"Ann's Sunday Game"
}
"""
If a game is played every nth week, here is the map for setting the
game frequency.
These examples match a GAME_NAME_MAPPING key name, 
setting Frequency will set the nth week to bill and
setting Offset will add a week to the nth week to bill (if it gets pushed back)
"""
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

#----------------------------------------------------------------------------------------------
#Start Billing Script
#----------------------------------------------------------------------------------------------

class Sheet_column_enum(Enum):
    NAME = 0
    EMAIL = 1
    IS_BILLED = 2
    PAY_PERIOD = 3
    GM_GAMES = 4
    PREPAID = 5
    LAST_BILL = 6
    
FILE_DATE_TAG = datetime.today().strftime('%Y-%m-%d-%H-%M-%S')
global_customer_list = []

def save_backup_csv():
    try:
        billing_csv = csv.reader(open(BILLING_FILE_NAME))
        billing_array = list(billing_csv)
        backup_file_path = BACKUP_DIR + FILE_DATE_TAG + "-" + BILLING_FILE_NAME
        if not os.path.isdir(BACKUP_DIR):
            os.makedirs(BACKUP_DIR)
        with open(backup_file_path, 'w', newline='', encoding='utf-8') as billing_file:
            writer = csv.writer(billing_file)
            writer.writerows(billing_array)
    except:
        print(f"ERROR: Cannot find {BILLING_FILE_NAME}")
        sys.exit(0)

def round_datetime_to_day(dt):
    return dt - timedelta(hours=dt.hour, minutes=dt.minute, seconds=dt.second, microseconds=dt.microsecond)

def count_weekdays_between_two_dates(start, end, frequency = 1, offset = 0):
    start_date  = datetime.strptime(start, DATE_FORMAT)
    end_date    = datetime.strptime(end, DATE_FORMAT)
    week = {}
    start_date = round_datetime_to_day(start_date)
    end_date = round_datetime_to_day(end_date)
    for i in range((end_date - start_date).days):
        if frequency > 1:
            week_count = (start_date + timedelta(days=i+1)).isocalendar()[1]
            if (week_count - offset)%frequency != 0:
                continue
        day = calendar.day_name[(start_date + timedelta(days=i+1)).weekday()]
        week[day] = week[day] + 1 if day in week else 1
    if 'Monday' not in week: week['Monday'] = 0
    if 'Tuesday' not in week: week['Tuesday'] = 0
    if 'Wednesday' not in week: week['Wednesday'] = 0
    if 'Thursday' not in week: week['Thursday'] = 0
    if 'Friday' not in week: week['Friday'] = 0
    if 'Saturday' not in week: week['Saturday'] = 0
    if 'Sunday' not in week: week['Sunday'] = 0
    return week

def calculate_next_billing_date(last, pay_frequancy):
    last_date = datetime.strptime(last, DATE_FORMAT)
    last_week_start = week_start = last_date - timedelta(days=last_date.weekday())
    if pay_frequancy == 'B':
        #Biweekely
        return (last_week_start + timedelta(days=14))
    elif pay_frequancy == 'M':
        #Monthly
        first_of_month = round_datetime_to_day(datetime.today()).replace(day=1)
        next_date = first_of_month + relativedelta(months=1) - timedelta(days=1)
        if (next_date - last_date).days < 27:
            next_date = next_date + relativedelta(months=1)
        return next_date
    else:
        #Weekely
        return (last_week_start + timedelta(days=7))

def sheet_update_prepaid_credits(name, updated_credit, row_index):
    name_col_index = Sheet_column_enum.NAME.value
    credit_col_index = Sheet_column_enum.PREPAID.value
    adjusted_row_index = row_index + 1 #offset popped header
    billing_csv = csv.reader(open(BILLING_FILE_NAME))
    billing_array = list(billing_csv)
    if billing_array[adjusted_row_index][name_col_index] == name:
        if DEBUG: log_and_print(f"DEBUG: Updating prepaid credit for: {name}")
        billing_array[adjusted_row_index][credit_col_index] = updated_credit
        if DEBUG: log_and_print(f"DEBUG: Prepaid credit updated successfuly to: {updated_credit}")
        with open(BILLING_FILE_NAME, 'w', newline='', encoding='utf-8') as billing_file:
            writer = csv.writer(billing_file)
            writer.writerows(billing_array)
        if DEBUG: log_and_print(f"DEBUG: Updated value saved in: {BILLING_FILE_NAME}")
        return True
    if DEBUG: log_and_print(f"DEBUG: Failed to match row index for: {name}")
    return False
    
def sheet_update_last_bill_sent(name, updated_last_bill_sent, row_index):
    name_col_index = Sheet_column_enum.NAME.value
    last_bill_col_index = Sheet_column_enum.LAST_BILL.value
    adjusted_row_index = row_index + 1 #offset popped header
    billing_csv = csv.reader(open(BILLING_FILE_NAME))
    billing_array = list(billing_csv)
    if billing_array[adjusted_row_index][name_col_index] == name:
        if DEBUG: log_and_print(f"DEBUG: Updating last bill send for: {name}")
        billing_array[adjusted_row_index][last_bill_col_index] = updated_last_bill_sent
        if DEBUG: log_and_print(f"DEBUG: Last bill sent updated successfuly to: {updated_last_bill_sent}")
        with open(BILLING_FILE_NAME, 'w', newline='', encoding='utf-8') as billing_file:
            writer = csv.writer(billing_file)
            writer.writerows(billing_array)
        if DEBUG: log_and_print(f"DEBUG: Updated value saved in: {BILLING_FILE_NAME}\n")
        return True
    if DEBUG: log_and_print(f"DEBUG: Failed to match row index for: {name}")
    return False

def formated_weekday_dict_string(weekdays):
    return ("Monday: " + str(weekdays['Monday']) + 
            "\tTuesday: " + str(weekdays['Tuesday']) +
            "\tWednesday: " + str(weekdays['Wednesday']) +
            "\tThursday: " + str(weekdays['Thursday']) +
            "\tFriday: " + str(weekdays['Friday']) +
            "\tSaturday: " + str(weekdays['Saturday']) +
            "\tSunday: " + str(weekdays['Sunday']))

def formated_game_items_string(game_items, prepaid_credits = 0):
    if prepaid_credits == 0:
        formated_string = "\n"
        i = 1
        for game in game_items:
            formated_string += f"\t\tITEM {i}\n"
            formated_string += f"\t\tGame Name\t: {game['Game_Name']}\n"
            formated_string += f"\t\tGM Name\t\t: {game['GM_Name']}\n"
            formated_string += f"\t\tWeekday\t\t: {game['Weekday_Played']}\n"
            formated_string += f"\t\tTotal Played\t: {game['Games_Played']}\n"
            formated_string += f"\t\tDates Played\t: {game['Dates_Played']}\n"
            formated_string += f"\t\tTotal Billed: {game['Games_Played']} games x {GAME_COST}$ = {(game['Games_Played']*GAME_COST)}$\n\n"
            i = i+1
        return formated_string
    else:
        running_prepaid_credit = prepaid_credits
        formated_string = ""
        i = 1
        for game in game_items:
            formated_string += f"\t\tITEM {i}\n"
            formated_string += f"\t\tGame Name\t: {game['Game_Name']}\n"
            formated_string += f"\t\tGM Name\t\t: {game['GM_Name']}\n"
            formated_string += f"\t\tWeekday\t\t: {game['Weekday_Played']}\n"
            formated_string += f"\t\tTotal Played\t: {game['Games_Played']}\n"
            formated_string += f"\t\tDates Played\t: {game['Dates_Played']}\n"
            if running_prepaid_credit == 0:
                formated_string += f"\t\tTotal Billed: {game['Games_Played']} games x {GAME_COST}$ = {(game['Games_Played']*GAME_COST)}$\n\n"
            elif running_prepaid_credit <= game['Games_Played']:
                formated_string += f"\t\tTotal Billed: ({game['Games_Played']} games - {running_prepaid_credit} prepaid credits) x {GAME_COST}$ = {((game['Games_Played']-running_prepaid_credit)*GAME_COST)}$\n"
                running_prepaid_credit = 0
                formated_string += f"\t\tRemaining Prepaid Credit: {running_prepaid_credit}\n\n"
            else:
                formated_string += f"\t\tTotal Billed: ({game['Games_Played']} games - {game['Games_Played']} prepaid credits) x {GAME_COST}$ = {((game['Games_Played']-game['Games_Played'])*GAME_COST)}$\n"
                running_prepaid_credit = running_prepaid_credit - game['Games_Played']
                formated_string += f"\t\tRemaining Prepaid Credit: {running_prepaid_credit}\n\n"
            i = i+1
        return formated_string

def is_frequency_set_in_game_items(game_items):
    has_frequency = False
    message = ""
    for game_item in game_items:
        if game_item['Frequency'] > 1:
            has_frequency = True
            message += f"\tWARNING: Game {game_item['Game_Name']} has a frequency of {game_item['Frequency']} and needs to be checked manualy!\n"
    return {
        'has_frequency':has_frequency,
        'message':message
    }

def log_and_print(message):
    print(message)
    log_file_path = LOG_DIR + "BillingLog-" + FILE_DATE_TAG + ".txt"
    if not os.path.isdir(LOG_DIR):
        os.makedirs(LOG_DIR)
    if not os.path.exists(log_file_path):
        with open(log_file_path, 'w') as log_file:
            log_file.write(message + "\n")
    else:
        with open(log_file_path, 'a') as log_file:
            log_file.write(message + "\n")

def create_error_log(error_customer_list):
    error_file_path = ERROR_DIR + "ManualBilling-" + FILE_DATE_TAG + ".txt"
    if not os.path.isdir(ERROR_DIR):
        os.makedirs(ERROR_DIR)
        
def send_paypal_post_grep():
    create_error_log(customer_list)
    return True

def weekday_date_list(start, end, weekday, pay_frequency):
    start_date = datetime.strptime(start, DATE_FORMAT)
    end_date = datetime.strptime(end, DATE_FORMAT)
    start_date = round_datetime_to_day(start_date)
    end_date = round_datetime_to_day(end_date)
    date_list = []
    if pay_frequency != 'W':
        for i in range((end_date - start_date).days):
            day = calendar.day_name[(start_date + timedelta(days=i+1)).weekday()]
            if(weekday == day): date_list.append((start_date + timedelta(days=i+1)).strftime(DATE_FORMAT))
    else:
        for i in range((end_date - start_date).days):
            day = calendar.day_name[(start_date + timedelta(days=i+1)).weekday()]
            if(weekday == day): date_list.append((start_date + timedelta(days=i+1)).strftime(DATE_FORMAT))
    return date_list

def run_billing():
    save_backup_csv()
    billing_csv = csv.reader(open(BILLING_FILE_NAME))
    billing_array = list(billing_csv)
    headers = billing_array.pop(0)
    custoner_count = len(billing_array)
    log_and_print(f"Processing {custoner_count} Customer Entries...")
    for i in range(custoner_count):
        has_error = False
        
        """
        customer = {
            'Name':<string>,
            'Email':<string>,
            'Is_Billed':<boolean>,
            'Pay_Frequency':<char>,
            'Prepaid_Credits':<int>,
            'Last_Bill_Sent':<string>,
            'Updated_Last_Bill_Sent':<string>,
            'Is_Late':<boolean>
            'Game_Items':[
                {
                    'Game_Name':<string>,
                    'GM_Name':<string>,
                    'Weekday_Played':<string>,
                    'Frequency':<int>,
                    'Offset':<int>,
                    'Games_Played':<int>,
                    'Dates_Played':[<string>]
                },...
            ],
            'Games_Played':<int>,
            'Dates_Played':[<string>],
            'Updated_Prepaid_Credits':<int>,
            'Games_Charged':<int>
        }
        """
        customer = {}
        current_csv_row = i
        
        #Parse customer info
        name = billing_array[i][Sheet_column_enum.NAME.value]
        customer['Name'] = name
        email = billing_array[i][Sheet_column_enum.EMAIL.value]
        customer['Email'] = email
        
        log_and_print(f"\n\nProccessing data for Customer: {name} at Email: {email}")
        
        #Check if Skipped
        is_billed = (billing_array[i][Sheet_column_enum.IS_BILLED.value] != 'N')
        customer['Is_Billed'] = is_billed
        if not is_billed:
            log_and_print(f"{name}:{email}\tIs Billable?: {is_billed}")
            log_and_print(f"{name}:{email}\tSkipping...")
            continue
        
        #Parse billing info
        pay_frequency = billing_array[i][Sheet_column_enum.PAY_PERIOD.value]
        if pay_frequency == '': pay_frequency = 'W'
        customer['Pay_Frequency'] = pay_frequency
        
        prepaid_credits = None
        try:
            prepaid_credits = int(billing_array[i][Sheet_column_enum.PREPAID.value])
        except:
            prepaid_credits = 0
        customer['Prepaid_Credits'] = prepaid_credits
        log_and_print(f"{name}:{email}\tIs Billable?: {is_billed}")
        log_and_print(f"{name}:{email}\tPay Frequency: {pay_frequency}")
        log_and_print(f"{name}:{email}\tPrepaid Credits: {prepaid_credits}")
        
        #Get date range data
        last_bill_sent = round_datetime_to_day(datetime.today())
        is_late = False
        updated_last_bill_sent = ''
        todays_date = round_datetime_to_day(datetime.today())
        if billing_array[i][Sheet_column_enum.LAST_BILL.value] != '':
            last_bill_sent = datetime.strptime(
                str(billing_array[i][Sheet_column_enum.LAST_BILL.value]), 
                DATE_FORMAT
            )
            next_billing_date = calculate_next_billing_date(
                billing_array[i][Sheet_column_enum.LAST_BILL.value],
                billing_array[i][Sheet_column_enum.PAY_PERIOD.value]
            )
            if IS_PAY_AHEAD:
                if todays_date >= next_billing_date:
                    updated_last_bill_sent = todays_date.strftime(DATE_FORMAT)
                    is_late = True
                elif todays_date < next_billing_date and todays_date >= last_bill_sent:
                    updated_last_bill_sent = next_billing_date.strftime(DATE_FORMAT)
                    if todays_date >= last_bill_sent + timedelta(days=1):
                        is_late = True
                else:
                    log_and_print(f"{name}:{email}\tSkipping: Next bill will be sent out on: {last_bill_sent.strftime(DATE_FORMAT)}")
                    continue
            else:
                if todays_date >= next_billing_date:
                    updated_last_bill_sent = todays_date.strftime(DATE_FORMAT)
                    if todays_date >= next_billing_date + timedelta(days=1):
                        is_late = True
                else:
                    log_and_print(f"{name}:{email}\tSkipping: Next bill will be sent out on: {next_billing_date.strftime(DATE_FORMAT)}")
                    continue
            log_and_print(f"{name}:{email}\tExpected next billing date: {next_billing_date.strftime(DATE_FORMAT)}")
            log_and_print(f"{name}:{email}\tLast Bill Sent: {last_bill_sent.strftime(DATE_FORMAT)}")
            log_and_print(f"{name}:{email}\tIs late?: {is_late}")
        else:
            log_and_print("WARNING: Missing 'Last Bill Sent' field, skipping")
            continue
        last_bill_sent = last_bill_sent.strftime(DATE_FORMAT)
        customer['Last_Bill_Sent'] = last_bill_sent
        customer['Updated_Last_Bill_Sent'] = updated_last_bill_sent
        customer['Is_Late'] = is_late
        
        #Get game item data
        game_items = []
        gms_played_under = set()
        customer_game_list = billing_array[i][Sheet_column_enum.GM_GAMES.value].split(',')
        customer_game_list = [game_handle.strip(' ') for game_handle in customer_game_list]
        for game_string in customer_game_list:
            game_item = {}
            game_parser = re.search(GAME_RE, game_string)
            if game_parser:
                if game_string in GAME_NAME_MAPPING:
                    game_item['Game_Name'] = GAME_NAME_MAPPING[game_string]
                else:
                    log_and_print(f"ERROR: {game_string} dosen't exist in GAME_NAME_MAPPING!")
                    has_error = True
                    continue
                game_item['GM_Name'] = game_parser.groups()[0]
                gms_played_under.add(game_item['GM_Name'])
                weekday = game_parser.groups()[1]
                if "M" in weekday: 
                    game_item['Weekday_Played'] = "Monday"
                    weekday = "Monday"
                elif "Tu" in weekday: 
                    game_item['Weekday_Played'] = "Tuesday"
                    weekday = "Tuesday"
                elif "W" in weekday: 
                    game_item['Weekday_Played'] = "Wednesday"
                    weekday = "Wednesday"
                elif "Th" in weekday: 
                    game_item['Weekday_Played'] = "Thursday"
                    weekday = "Thursday"
                elif "F" in weekday: 
                    game_item['Weekday_Played'] = "Friday"
                    weekday = "Friday"
                elif "Sa" in weekday: 
                    game_item['Weekday_Played'] = "Saturday"
                    weekday = "Saturday"
                else: 
                    game_item['Weekday_Played'] = "Sunday"
                    weekday = "Sunday"
                frequency = 1
                offset = 0
                if game_string in GAME_FREQUENCY:
                    frequency = GAME_FREQUENCY[game_string]['Frequency']
                    offset = GAME_FREQUENCY[game_string]['Offset']
                game_item['Frequency'] = frequency
                game_item['Offset'] = offset
                possible_billing_dates = count_weekdays_between_two_dates(last_bill_sent,updated_last_bill_sent,frequency,offset)
                games_played = possible_billing_dates[weekday]
                game_item['Games_Played'] = games_played
                dates_played_on = weekday_date_list(last_bill_sent, updated_last_bill_sent, weekday, pay_frequency)
                game_item['Dates_Played'] = dates_played_on
                log_and_print(f"{name}:{email}\t\tGame {game_item['Game_Name']} for GM {game_item['GM_Name']} on {weekday}:")
                log_and_print(f"{name}:{email}\t\t\tWeekdays Days Between {last_bill_sent} and {updated_last_bill_sent} are:")
                log_and_print(f"{name}:{email}\t\t\t{formated_weekday_dict_string(possible_billing_dates)}")
                log_and_print(f"{name}:{email}\t\t\tBillable Days are {dates_played_on} for {games_played} total games played")
                game_items.append(game_item)
        customer['Game_Items'] = game_items
        customer['GMs_Played_Under'] = list(gms_played_under)
        total_games_played = 0
        total_dates_played = set()
        for game_item in game_items:
            total_games_played = total_games_played + game_item['Games_Played']
            total_dates_played.update(game_item['Dates_Played'])
        customer['Games_Played'] = total_games_played
        customer['Dates_Played'] = list(total_dates_played)
        
        if has_error:
            continue
        
        #Get prepaid credit updates and total charged data
        charged_games_played = 0
        update_prepaid_credits = 0
        if prepaid_credits >= total_games_played:
            update_prepaid_credits = prepaid_credits - total_games_played
            charged_games_played = 0
        else:
            charged_games_played = total_games_played - prepaid_credits
            update_prepaid_credits = 0
        customer['Updated_Prepaid_Credits'] = update_prepaid_credits
        customer['Games_Charged'] = charged_games_played
        
        #Update CSV tables and send invoices
        is_successfully_procesed = False
        if charged_games_played > 0:  
            is_successfully_procesed = send_paypal_post_grep(customer)
        else:
            is_successfully_procesed = True
        sheet_update_prepaid_credits(name, update_prepaid_credits, current_csv_row)
        sheet_update_last_bill_sent(name, updated_last_bill_sent, current_csv_row)
        if is_successfully_procesed: 
            print(f"{name}:{email}\tSucessfully processed paypal invoice for {name}")
        else:
            log_and_print(f"WARNING: A manual Billing File has been created for {name}")
        global_customer_list.append(customer)

"""
customer = {
    'Name':<string>,
    'Email':<string>,
    'Is_Billed':<boolean>,
    'Pay_Frequency':<char>,
    'Prepaid_Credits':<int>,
    'Last_Bill_Sent':<string>,
    'Updated_Last_Bill_Sent':<string>,
    'Is_Late':<boolean>
    'Game_Items':[
        {
            'Game_Name':<string>,
            'GM_Name':<string>,
            'Weekday_Played':<string>,
            'Frequency':<int>,
            'Offset':<int>,
            'Games_Played':<int>,
            'Dates_Played':<string>
        },...
    ],
    'GMs_Played_Under':[<string>],
    'Games_Played':<int>,
    'Dates_Played':[<string>],
    'Updated_Prepaid_Credits':<int>,
    'Games_Charged':<int>
}
"""      
def send_paypal_post_grep(customer):
    messages = ""
    has_warnings = False
    frequency_response = is_frequency_set_in_game_items(customer['Game_Items'])
    if frequency_response['has_frequency']:
        messages += frequency_response['message']
        has_warnings = True
    if (customer['Games_Charged']*GAME_COST) > STOP_GAP:
        messages += f"\tWARNING: Invoice is more than {STOP_GAP}$ and will need manual processing!\n"
        has_warnings = True
    if not ENABLE_PP_API:
        messages += f"\tWARNING: PP API is currently disabled!\n"
        has_warnings = True
    if has_warnings:
        create_manual_billing(customer, messages)
        return False
    pp_api_response = run_customer_data_over_paypal_api(customer)
    if not pp_api_response['successfully_processed_invoice']:
        messages += f"\tERROR: Paypal Invoices failed to send!\n{pp_api_response['error']}\n"
        create_manual_billing(customer, messages)
        return False
    return True
    
def create_manual_billing(customer, messages):
    name = customer['Name']
    email = customer['Email']
    is_billed = customer['Is_Billed']
    pay_frequency = customer['Pay_Frequency']
    prepaid_credits = customer['Prepaid_Credits']
    last_bill_sent = customer['Last_Bill_Sent']
    updated_last_bill_sent = customer['Updated_Last_Bill_Sent']
    is_late = customer['Is_Late']
    game_items = customer['Game_Items']
    gms_played_under = customer['GMs_Played_Under']
    games_played = customer['Games_Played']
    dates_played = customer['Dates_Played']
    updated_prepaid_credits = customer['Updated_Prepaid_Credits']
    games_charged = customer['Games_Charged']
    
    error_file_path = ERROR_DIR + "ManualBilling-" + FILE_DATE_TAG + ".txt"
    if not os.path.isdir(ERROR_DIR):
        os.makedirs(ERROR_DIR)
    error_string = (
        f"Manual Billing info for {name} at email {email}\n" +
        f"Name: {name}\n" +
        f"Email: {email}\n" +
        f"Billed games after prepaid credits: {games_charged}\t\tTotal game count: {games_played}\n" +
        f"Prepaid Credits used: {prepaid_credits - updated_prepaid_credits}\t\t\tPrepaid Credits remaining: {updated_prepaid_credits}\n" +
        f"Bill sent on: {updated_last_bill_sent}\tBilled days are between ({last_bill_sent} - {updated_last_bill_sent}]\n" +
        f"Game Items under GMs {gms_played_under}\n\n"
    )
    error_string += formated_game_items_string(game_items, prepaid_credits = 0)
    error_string += (
        f"Total Games Charged: {games_charged} x {GAME_COST}$ = {games_charged*GAME_COST}$\n" +
        f"Remaining Prepaid Credit: {updated_prepaid_credits}\n" +
        f"Dates played on: {dates_played}\n\n" +
        f"{messages}\n"
    )
    if not os.path.exists(error_file_path):
        with open(error_file_path, 'w') as log_file:
            log_file.write(error_string + "\n\n\n\n\n")
    else:
        with open(error_file_path, 'a') as log_file:
            log_file.write(error_string + "\n\n\n\n\n")

def run_customer_data_over_paypal_api(customer):
    try:
        paypal_url = get_pp_url()
        oauth_url = f'{paypal_url}/v1/oauth2/token'
        oauth_response = requests.post(
            oauth_url,
            headers={
            'Accept': 'application/json',
            'Accept-Language': 'en_US'
            },
            auth=get_pp_auth(),
            data={'grant_type': 'client_credentials'}
        )
        if DEBUG:
            print("TESTING OATH RESPONSE:")
            print(oauth_response)
            print(oauth_response.json())
        oauth_response_json = oauth_response.json()
        access_token = oauth_response_json['access_token']
        invoice_headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
            'Prefer': 'return=representation',
        }
        invoice_data = pp_form_invoice_json_string(customer)
        if DEBUG:
            print("INVOICE JSON")
            print(invoice_data)
        draft_response = requests.post(f"{get_pp_url()}/v2/invoicing/invoices", headers=invoice_headers, data=invoice_data)
        if DEBUG:
            print("TESTING DRAFT RESPONSE:")
            print(draft_response)
            print(draft_response.json())
        draft_response_json = draft_response.json()
        invoice_id = draft_response_json['id'] # invoice_id
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
        }
        data = '{ "send_to_invoicer": true }'
        send_response = requests.post(f"{get_pp_url()}/v2/invoicing/invoices/{invoice_id}/send", headers=headers, data=data)
        if DEBUG:
            print("TESTING SEND RESPONSE:")
            print(send_response)
        
        return {'successfully_processed_invoice' : True}
    except Exception as e:
        return {
            'successfully_processed_invoice' : False,
            'error': str(e)
        }

#-------------------------------------------------------------------
#PAYPAL V2-INVOICE HELPER FUNCTIONS, FORMATS, TEMPLATES, AND EXAMPLES
#-------------------------------------------------------------------
def pp_form_invoice_json_string(customer):
    invoice = {
      "detail": {
        "invoice_number": get_invoice_number(),
        "invoice_date": round_datetime_to_day(datetime.today()).strftime(INVOICE_DATE_FORMAT),
        "currency_code": "USD",
        "note": pp_note_from_customer_data(customer),
        "terms_and_conditions": PP_TERMS_AND_CONDITIONS,
        "payment_term": { 
            "term_type": "DUE_ON_DATE_SPECIFIED", 
            "due_date": pp_due_date() 
        }
      },
      "invoicer": {
        "email_address": get_merchant_email()
      },
      "primary_recipients": [
        {
          "billing_info": {
            "email_address": customer['Email']
          }
        }
      ],
      "items": pp_item_list_from_customer_data(customer),
      "configuration": {
        "allow_tip": True
      }
    }
    return json.dumps(invoice)
INVOICE_DATE_FORMAT = '%Y-%m-%d'
def pp_due_date():
    now = datetime.now()
    year = now.year
    month = now.month
    end_of_current_month = round_datetime_to_day(datetime(year,month,1)) + relativedelta(months=1) - relativedelta(days=1)
    return end_of_current_month.strftime(INVOICE_DATE_FORMAT)
"""
customer = {
    'Name':<string>,
    'Email':<string>,
    'Is_Billed':<boolean>,
    'Pay_Frequency':<char>,
    'Prepaid_Credits':<int>,
    'Last_Bill_Sent':<string>,
    'Updated_Last_Bill_Sent':<string>,
    'Is_Late':<boolean>
    'Game_Items':[
        {
            'Game_Name':<string>,
            'GM_Name':<string>,
            'Weekday_Played':<string>,
            'Frequency':<int>,
            'Offset':<int>,
            'Games_Played':<int>,
            'Dates_Played':<string>
        },...
    ],
    'GMs_Played_Under':[<string>],
    'Games_Played':<int>,
    'Dates_Played':[<string>],
    'Updated_Prepaid_Credits':<int>,
    'Games_Charged':<int>
}
"""
"""
"items": [
    {
      "name": "Service",
      "description": "..."
      "quantity": "1",
      "unit_amount": {
        "currency_code": "USD",
        "value": "100.00"
      }
    },
    ...
  ]
"""
def pp_item_list_from_customer_data(customer):
    game_items = customer['Game_Items']
    prepaid_credits = customer['Prepaid_Credits']
    if prepaid_credits == 0:
        item_list = []
        for game_item in game_items:
            game_name = game_item['Game_Name']
            gm_name = game_item['GM_Name']
            weekday_played = game_item['Weekday_Played']
            games_played = game_item['Games_Played']
            quantity = games_played
            pp_item = {}
            pp_item['name'] = f"{gm_name} {weekday_played} {game_name}"
            pp_item['description'] = f"{gm_name}'s {weekday_played} game {game_name}, played on days {games_played}"
            pp_item['quantity'] = quantity
            pp_item['unit_amount'] = {
                "currency_code": "USD",
                "value": str(GAME_COST)
            }
            item_list.append(pp_item)
    else:
        item_list = []
        running_prepaid_credit = prepaid_credits
        for game_item in game_items:
            game_name = game_item['Game_Name']
            gm_name = game_item['GM_Name']
            weekday_played = game_item['Weekday_Played']
            games_played = game_item['Games_Played']
            quantity = None
            if running_prepaid_credit == 0:
                quantity = games_played
            elif running_prepaid_credit <= games_played:
                quantity = games_played - running_prepaid_credit
                running_prepaid_credit = running_prepaid_credit - games_played
            else:
                quantity = 0
                running_prepaid_credit = running_prepaid_credit - games_played
            if quantity == 0:
                continue
            pp_item = {}
            pp_item['name'] = f"{gm_name} {weekday_played} {game_name}"
            pp_item['description'] = f"{gm_name}'s {weekday_played} game {game_name}, played on days {games_played}"
            pp_item['quantity'] = quantity
            pp_item['unit_amount'] = {
                "currency_code": "USD",
                "value": str(GAME_COST)
            }
            item_list.append(pp_item)
    return item_list
"""
customer = {
    'Name':<string>,
    'Email':<string>,
    'Is_Billed':<boolean>,
    'Pay_Frequency':<char>,
    'Prepaid_Credits':<int>,
    'Last_Bill_Sent':<string>,
    'Updated_Last_Bill_Sent':<string>,
    'Is_Late':<boolean>
    'Game_Items':[
        {
            'Game_Name':<string>,
            'GM_Name':<string>,
            'Weekday_Played':<string>,
            'Frequency':<int>,
            'Offset':<int>,
            'Games_Played':<int>,
            'Dates_Played':<string>
        },...
    ],
    'GMs_Played_Under':[<string>],
    'Games_Played':<int>,
    'Dates_Played':[<string>],
    'Updated_Prepaid_Credits':<int>,
    'Games_Charged':<int>
}
"""
def pp_note_from_customer_data(customer):
    name = customer['Name']
    gms_played_under = customer['GMs_Played_Under']
    games_played = customer['Games_Played']
    dates_played = customer['Dates_Played']
    updated_prepaid_credits = customer['Updated_Prepaid_Credits']
    games_charged = customer['Games_Charged']
    game_items = customer['Game_Items']
    prepaid_credits = customer['Prepaid_Credits']
    due_date = pp_due_date()
    formated_string = ""
    if prepaid_credits == 0:
        formated_string += f"""
            {name} played {games_played} games under GMs {gms_played_under} on days {dates_played}.\n
            Starting Prepaid Credits: {prepaid_credits},\n
            Games Played: {games_played},\n
            Games Charged: {games_charged},\n
            Remaining Prepaid Credits: {updated_prepaid_credits}.\n
        """
        for game in game_items:
            formated_string += f"\n"
            formated_string += f"\t\tGame Name\t: {game['Game_Name']}\n"
            formated_string += f"\t\tGM Name\t\t: {game['GM_Name']}\n"
            formated_string += f"\t\tWeekday\t\t: {game['Weekday_Played']}\n"
            formated_string += f"\t\tTotal Played\t: {game['Games_Played']}\n"
            formated_string += f"\t\tDates Played\t: {game['Dates_Played']}\n"
            formated_string += f"\t\tBilled: {game['Games_Played']} games x {GAME_COST}$ = {(game['Games_Played']*GAME_COST)}$\n\n"
    else:
        formated_string += f"""
            {name} played {games_played} games under GMs {gms_played_under} on days {dates_played}.\n
            Starting Prepaid Credits: {prepaid_credits},\n
            Games Played: {games_played},\n
            Games Charged: {games_charged},\n
            Remaining Prepaid Credits: {updated_prepaid_credits}.\n
        """
        running_prepaid_credit = prepaid_credits
        for game in game_items:
            formated_string += f"\n"
            formated_string += f"\t\tGame Name\t: {game['Game_Name']}\n"
            formated_string += f"\t\tGM Name\t\t: {game['GM_Name']}\n"
            formated_string += f"\t\tWeekday\t\t: {game['Weekday_Played']}\n"
            formated_string += f"\t\tTotal Played\t: {game['Games_Played']}\n"
            formated_string += f"\t\tDates Played\t: {game['Dates_Played']}\n"
            if running_prepaid_credit == 0:
                formated_string += f"\t\tBilled: {game['Games_Played']} games x {GAME_COST}$ = {(game['Games_Played']*GAME_COST)}$\n\n"
            elif running_prepaid_credit <= game['Games_Played']:
                formated_string += f"\t\tBilled: ({game['Games_Played']} games - {running_prepaid_credit} prepaid credits) x {GAME_COST}$ = {((game['Games_Played']-running_prepaid_credit)*GAME_COST)}$\n"
                running_prepaid_credit = 0
                formated_string += f"\t\tRemaining Prepaid Credit: {running_prepaid_credit}\n\n"
            else:
                formated_string += f"\t\tBilled: ({game['Games_Played']} games - {game['Games_Played']} prepaid credits) x {GAME_COST}$ = {((game['Games_Played']-game['Games_Played'])*GAME_COST)}$\n"
                running_prepaid_credit = running_prepaid_credit - game['Games_Played']
                formated_string += f"\t\tRemaining Prepaid Credit: {running_prepaid_credit}\n\n"
    formated_string += f"Total Billed: {games_charged} x {GAME_COST}$ = {games_charged*GAME_COST}$"
    if len(formated_string) > 3999:
        return formated_string[:3998]
    return formated_string

def generate_short_guid_string():
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    number = int.from_bytes(uuid.uuid4().bytes, 'big')
    result = ""
    while number > 0:
        result = digits[number % 36] + result
        number //= 36
    return result
    
def get_pp_url():
    if IS_SANDBOX:
        return 'https://api-m.sandbox.paypal.com'
    else:
        return 'https://api-m.paypal.com'
        
def get_pp_auth():
    if IS_SANDBOX:
        return (SANDBOX_CLIENT_ID, SANDBOX_SECRET)
    else:
        return (LIVE_CLIENT_ID, LIVE_SECRET)

def get_merchant_email():
    if IS_SANDBOX:
        return SANDBOX_MERCHANT_EMAIL
    else:
        return LIVE_MERCHANT_EMAIL
        
def get_invoice_number():
    try:
        if os.path.exists("invoice_num.txt"):
            with open('invoice_num.txt', 'r') as file:
                num_string = file.read()
            invoice_num = int(num_string[1:])
            invoice_num += 1
            invoice_num_string = f"A{invoice_num}"
            with open('invoice_num.txt', "w") as file:
                file.write(invoice_num_string)
            return invoice_num_string
        else:
            with open('invoice_num.txt', "w") as file:
                file.write("A1")
            return "A1"
    except:
        with open('invoice_num.txt', "w") as file:
            file.write("A1")
        return "A1"

run_billing()