import itertools
import random
from itertools import combinations
import sys


teams = [
    "Thunderbolts", "Firestorm", "Mavericks", "Avalanche",

    "Hurricanes", "Dragons", "Wildcats","Titans"

   , "Stingrays", "Chargers","Braves", "Generals"

    , "Vultures", "Devils", "Greyhounds", "Blizzard"
]
times = ['6:30','7:30', '8:30','9:30']


# for manually inputted parameters
nteams = int(sys.argv[1])
ntimes = int(sys.argv[2])
nfields = int(sys.argv[3])
nweeks = int(sys.argv[4])
games_in_a_week = int(sys.argv[5])

debug_mode = True
'''

nteams = 12
ntimes = 3
nfields = 4
nweeks = 11
games_in_a_week = 2
'''
##################################################################################################


teams = teams[0:nteams]
times = times[0:ntimes]
ngames = ntimes * nfields * nweeks

# Generate all possible pairs of teams
team_pairs = list(itertools.combinations(sorted(teams), 2))
random.shuffle(team_pairs)

#counters
break_counter = 0
team_play_count = [[0] * nteams for _ in range(nteams)] #counts number of times each team has played each other
team_game_count = {team: 0 for team in teams} # counts number of games each team has played
team_break_count = {team: 0 for team in teams} # number of breaks
temp_break_count = {team: 0 for team in teams}#temp for incrementing
team_time_slot_counters = {team: {time: 0 for time in times} for team in teams}


class Game:
    def __init__(self, time_slot, field, week):
        self.week = week
        self.time_slot = time_slot
        self.field = field
        self.domain = team_pairs.copy()  # All possible pairs of teams
        self.assigned_teams = None  # Assigned team pair

    def assign_teams(self, team_pair):
        self.assigned_teams = team_pair

    def unassign_teams(self):
        self.assigned_teams = None


class CSP:
    def __init__(self, games, constraints):
        self.games = games
        self.constraints = constraints
        self.variables = games  # For convenience, games are the variables



#################PRINTING FUNCTIONS ####################################################
def print_state(solution):
    print("game count:")
    print(team_game_count)
    print("break count")
    print(team_break_count)
    print("\nTeam Play Count Matrix:")
    print("Teams".ljust(15) + " ".join(team.ljust(15) for team in teams))
    for i, team in enumerate(teams):
        print(team.ljust(15) + " ".join(str(count).ljust(15) for count in team_play_count[i]))

    for team, time_slots in team_time_slot_counters.items(): #print time slot
        print(f"{team}:")
        for time_slot, count in time_slots.items():
            print(f"  {time_slot}: {count}")
        print()
    for game in solution:
        print(f"Week {game.week + 1}, Time {game.time_slot}, Field {game.field + 1}: {game.assigned_teams}")

def db_print(item):
    if debug_mode:
        print(item)


########################## BEGIN INFERENCE AND PRUNING FUNCTIONS ##############################################

def inference(assignment, csp, i):  # Return a CSP object with smaller domain space using heuristics
    new_csp = csp
    recent_pair = list(assignment.items())[len(assignment) - 1][1]
    if (len(times)) % 2 == 1 and games_in_a_week > 1: # if odd n timeslots
        new_csp = softball_pruning_algo(new_csp, assignment, recent_pair)
    #else:
        #new_csp = consecutive_pruning_algo(new_csp, assignment, recent_pair)

    return new_csp

def softball_pruning_algo(csp, assignment, recent_pair):
    current_game = list(assignment.items())[-1][0] #get current game object and data
    current_week = current_game.week
    time_slot = current_game.time_slot

    if current_week == 4:
        return csp


    # Pruning based on 6:30 game
    if time_slot == '6:30' and current_week > 0 and current_week != nweeks / 2:
        for team in recent_pair:
            if (team_break_count[team] > 0 and current_week < 3) or (team_break_count[team] > 1 and current_week >= 3): # if assigned team has 1 break before halfway or 2 breaks after
                # Prune team with break from this week’s 8:30 games
                csp = prune_team_from_time_slot(csp, current_week, team, '8:30')

    # Pruning based on last 6:30 game of the week
    if is_last_6_30_game_of_week(assignment, current_game) and current_week > 0 and current_week != nweeks / 2:
        # Find all teams in 6:30 games this week without break yet
        teams_with_breaks = [
            team for game, pair in assignment.items()
            if game.week == current_week and game.time_slot == '6:30'
            for team in pair
            if (team_break_count[team] > 0 and current_week < nweeks / 2) or (team_break_count[team] > 1 and current_week >= nweeks / 2)
        ]

        if len(teams_with_breaks) == nfields:
            remaining_teams = [
                team for game, pair in assignment.items()
                if game.week == current_week and game.time_slot == '6:30'
                for team in pair
                if team not in teams_with_breaks
            ]
            remaining_teams = remaining_teams[0:4]
            # Prune remaining teams from 7:30 games
            for team in remaining_teams:
                csp = prune_team_from_time_slot(csp, current_week, team, '7:30')
            # Prune 6:30 games with breaks from 8:30 games
            #after pruning use generate unique combos to make domains for 7:30s all combos of current csp
            for team in teams_with_breaks:
                csp = prune_team_from_time_slot(csp, current_week, team, '8:30')

            for game in csp.variables:
                if (game.time_slot == '7:30' or game.time_slot == '8:30') and game.week == current_week:
                    game.domain = generate_unique_combinations(game.domain)


    return csp

def consecutive_pruning_algo(csp, assignment, recent_pair):
    current_game = list(assignment.items())[-1][0]
    current_time_slot_index = times.index(current_game.time_slot)
    current_time_slot = current_game.time_slot

    # Check if the current time slot is even indexed and the last field in the slot
    if current_time_slot_index % 2 == 0 and current_game.field == nfields - 1:
        next_time_slot_index = current_time_slot_index + 1
        if next_time_slot_index < len(times):  # Ensure there's a next time slot
            next_time_slot = times[next_time_slot_index]
            current_week = current_game.week

            # Find teams scheduled in the same week and time slot as the most recent assignment
            teams_scheduled_current_slot = [
                team for game, pair in assignment.items()
                if game.week == current_week and game.time_slot == current_time_slot
                for team in pair
            ]

            # Find teams not scheduled in the current slot
            teams_not_scheduled = [team for team in teams if team not in teams_scheduled_current_slot]

            # Prune teams not scheduled in the current slot from the next time slot
            for team in teams_not_scheduled:
                csp = prune_team_from_time_slot(csp, current_week, team, next_time_slot)

    return csp


def prune_team_from_time_slot(csp, week, team, time_slot):
    for game in csp.variables:
        if game.week == week and game.time_slot == time_slot:
            game.domain = [pair for pair in game.domain if team not in pair]
    return csp

def is_last_6_30_game_of_week(assignment, current_game):
    current_week = current_game.week
    games_this_week = [game for game in assignment.keys() if game.week == current_week and game.time_slot == '6:30']
    last_field_for_week = max(game.field for game in games_this_week)
    return current_game.time_slot == '6:30' and 3 == last_field_for_week

def prune_future_domain_space(csp, current_week, recent_pair):
    for game in csp.variables:
        if game.week > current_week and game.week < nweeks - 1:
            game.domain = [pair for pair in game.domain if pair != recent_pair]
    return csp



def print_current_schedule(assignment):
    for game, team_pair in assignment.items():
        print(f"Week {game.week + 1}, Time {game.time_slot}, Field {game.field + 1}: {game.assigned_teams}")


########################## BEGIN BOOKEEPING FUNCTIONS ##############################################

def increment_counters(assignment,var, value):
    global break_counter
    global temp_break_count
    week = var.week
    team_game_count[value[0]] += 1
    team_game_count[value[1]] += 1

    team_play_count[teams.index(value[0])][teams.index(value[1])] += 1
    team_play_count[teams.index(value[1])][teams.index(value[0])] += 1

    team_time_slot_counters[value[0]][var.time_slot] += 1
    team_time_slot_counters[value[1]][var.time_slot] += 1

    pair = causes_break(assignment,week,value[0],value[1],var)
    temp_break_count = team_break_count
    if(pair != None):
        for team in pair:
            team_break_count[team] += 1
        break_counter += len(pair)



def decrement_counters(assignment,var,value):
    global break_counter
    week = var.week

    team_game_count[value[0]] -= 1
    team_game_count[value[1]] -= 1

    team_play_count[teams.index(value[0])][teams.index(value[1])] -= 1
    team_play_count[teams.index(value[1])][teams.index(value[0])] -= 1

    team_time_slot_counters[value[0]][var.time_slot] -= 1
    team_time_slot_counters[value[1]][var.time_slot] -= 1

    pair = causes_break(assignment, week, value[0], value[1], var)
    if (pair != None):
        for team in pair:
            team_break_count[team] -= 1
        break_counter -= len(pair)



####################################################################################

#main AC -3 function

def recursive_backtracking(assignment, csp):


    if len(assignment) == len(csp.variables):
        return assignment  # All variables are assigned, return the solution

    var = select_unassigned_variable(assignment, csp)
    db_print("CURRENT STATE: ")
    if debug_mode:
        print_state(assignment)
    db_print("SEARCHING FOR SOLUTION TO GAME: "+ str(len(assignment.items())+1)+", WEEK "+str(var.week+1)+" FIELD "+str(var.field+1)+", TIME  "+var.time_slot)

    for value in order_domain_values(var, assignment, csp):
        db_print("trying team pair "+str(value))
        increment_counters(assignment,var,value)
        if is_consistent(var, value, assignment, csp):
            db_print("CONSISTANT")
            var.assign_teams(value)
            assignment[var] = value
            new_csp = inference(assignment,csp,len(assignment)-1)
            result = recursive_backtracking(assignment, new_csp)
            if result is not None:  # This is the end, it returns our completed assignment
                return result
            del assignment[var]  # Backtrack
            var.unassign_teams()  # Reset assignment
        decrement_counters(assignment,var,value)
    db_print("FAIL")

    return None


def is_consistent(var, value, assignment, csp):
    var.assign_teams(value)
    assignment[var] = value
    team1 = var.assigned_teams[0]
    team2 = var.assigned_teams[1]
    for constraint in csp.constraints:  # For each constraint
        if not constraint(csp, assignment,var,team1,team2):
            del assignment[var]  # Remove temporary assignment
            var.unassign_teams()  # Reset assignment
            return False
    del assignment[var]  # Remove temporary assignment
    var.unassign_teams()  # Reset assignment
    return True

#########################BEGIN CONSTRAINT FUNCTIONS####################################
def no_conflicts(csp, assignment,var,a,b):  # make sure team's arent scheduled for 2 games at once
    assignment_items = list(assignment.items())
    n = len(assignment.items()) - 1

    time_slot = var.time_slot

    while n >= 1 and assignment_items[n-1][0].time_slot == time_slot and assignment_items[n-1][0].week == var.week:
        n -= 1

    a_count = 0
    b_count = 0
    while n < len(assignment.items()):
        if a in assignment_items[n][0].assigned_teams:
            if a_count == 1:
                db_print("DOESNT NO CONFLICTS ("+str(a)+")")
                return False
            else:
                a_count += 1
        if b in assignment_items[n][0].assigned_teams:
            if b_count == 1:
                db_print("DOESNT NO CONFLICTS (" + str(b) + ")")
                return False
            else:
                b_count += 1
        n += 1
    return True


def plays_each_team(csp, assignment, var,team1, team2):
    # Check if the difference between the min and max values in team_play_count is less than 3
    flattened_counts = [
        team_play_count[i][j]
        for i in range(len(team_play_count))
        for j in range(len(team_play_count[i]))
        if i != j
    ]

    # Check the difference between the min and max values in the flattened list
    if (max(flattened_counts) - min(flattened_counts) > 1):
        db_print("DOESNT PLAY EACH TEAM BALANCED")
        return False

    # if uses breaks check if we just assigned this team in the previous time slot, if so we ccan allow a

    return True


def has_enough_breaks(var,team1,team2):
    min_break = min(team_break_count.values())
    max_break = max(team_break_count.values())

    if max_break - min_break > 1:
        return True
    return False


def respects_break_scheduling(csp,assignment,var,team1,team2): # makes sure instances with breaks dont violate break rules
    if causes_break(assignment, var.week, team1, team2, var) != None:

        if has_enough_breaks(var,team1,team2):
            return False
        #check if this time is 9:30 and the one earlier in the week is a 6:30
        if var.time_slot == '9:30':
            breaks = causes_break(assignment, var.week, team1, team2, var)
            assignment_items = list(assignment.items())
            n = len(assignment.items()) - 1
            while assignment_items[n][0].week == var.week and n >= 0:  # go back to 6:30 games of current week
                if assignment_items[n][0].time_slot == '6:30':
                    for team in breaks:
                        if team in assignment_items[n][0].assigned_teams:
                            db_print("2 HOUR GAP ("+team+")")
                            return False
                n -= 1
            pair = []



    if ntimes == 3:
        if var.time_slot == '6:30' and (var.field > 1) and var.week > 1 and var.week != 3:
            teams_at_6 = []
            for game in assignment.items(): # count number of teams at 6:30  this week with no breaks
                if game[0].week == var.week and game[0].time_slot == '6:30':
                    for team in game[0].assigned_teams:
                        if temp_break_count[team] == 0 or (temp_break_count[team] == 1 and var.week > 2):
                            teams_at_6.append(team)
            if (len(teams_at_6) < 2 and var.field == 2) or (len(teams_at_6) != 4 and var.field == 3): # need 2 by the 3rd field and 4 by the 4th (last)
                db_print("VIOLATES 630 RULE")
                return False

        elif var.time_slot == '7:30' and (var.field > 1) and (var.week == 4):
            teams_with_break = []
            for game in assignment.items(): # count number of teams at 7:30 with break
                if game[0].week == var.week and game[0].time_slot == '7:30':
                    for team in game[0].assigned_teams:
                        if temp_break_count[team] == 2 or temp_break_count[team] == 1 and var.week <= 2:
                            teams_with_break.append(team)
            if (len(teams_with_break) < 2 and var.field == 2) or (len(teams_with_break) != 4 and var.field == 3):
                db_print("VIOLATES 7:30 RULE")
                return False

            elif var.time_slot == '7:30' and (var.field < 2) and var.week != 4:
                teams_with_games_this_week = []
                for game in assignment.items():  # count number of teams at 6:30 with no breaks
                    if game[0].week == var.week:
                        for team in game[0].assigned_teams:
                                teams_with_games_this_week.append(team)
                if (len(teams_with_games_this_week) < (nteams-2) and var.field == 1) or (len(teams_with_break) < nteams and var.field == 0):
                    return False

    return True

def respects_consecutive_scheduling(csp, assignment, var, team1, team2):
    current_game = var
    current_time_slot_index = times.index(current_game.time_slot)

    if current_time_slot_index % 2 == 1:  # if odd numbered time slot
        previous_time_slot_index = current_time_slot_index - 1
        previous_time_slot = times[previous_time_slot_index]

        previous_time_slot_teams = [
            team for game, pair in assignment.items()
            if game.week == current_game.week and game.time_slot == previous_time_slot
            for team in pair
        ]

        if team1 not in previous_time_slot_teams or team2 not in previous_time_slot_teams:
            db_print("DOESNT RESPECT CONSECUTIVE SCHEDULING")
            return False
    return True


def respects_alternating_times(csp, assignment, var, team1, team2):
    team1_counts = team_time_slot_counters[team1]
    team2_counts = team_time_slot_counters[team2]

    # Get the minimum count of usage for any time slot for both teams
    min_usage_team1 = min(team1_counts.values())
    min_usage_team2 = min(team2_counts.values())




    if len(assignment) == ngames:
        teams_with_flat_counts = 0

        # Iterate through all teams and check their time slot counts
        for team, counts in team_time_slot_counters.items():
            min_usage = min(counts.values())
            max_usage = max(counts.values())

            if ntimes <= 2 and max_usage - min_usage != 0:
                return False

            # Check if the team has flat time counts (same number of time slots played in)
            if max_usage - min_usage == 0:
                teams_with_flat_counts += 1
            elif max_usage - min_usage > 3:
                db_print("DOESNT RAT")
                return False

        # Ensure at least half of the teams have flat time counts
    return True
def each_team_plays(csp, assignment,var,team1,team2):  # make sure each team plays the same amount of games, every week
    games_per_team = (var.week +1) * games_in_a_week
    assignment_items = list(assignment.items())
    n = len(assignment.items()) - 1

    team_pair = assignment_items[n][0].assigned_teams

    if (len(assignment) == len(csp.variables) or (len(assignment) % (nfields * ntimes) == 0 and len(assignment) != 0)):
        for team in teams:
            if team_game_count[team] != games_per_team:
                db_print("DOESNT BALANCE GAMES PER TEAM")
                return False
        return True
    if games_in_a_week == 1:
        for team in teams:
            if team_game_count[team] > games_per_team:
                db_print("DOESNT BALANCE GAMES PER TEAM")
                return False

    return True



#########################BEGIN HELPER FUNCTIONS########################################
def select_unassigned_variable(assignment, csp):
    for var in csp.variables:
        if var not in assignment:
            return var
    return None


def order_domain_values(var, assignment, csp):
    valid_pairs = []
    assignment_items = list(assignment.items())
    week = 1

    if len(assignment_items) > 0:
        week = var.week + 1
    max_games = week * games_in_a_week
    for pair in var.domain:
        team1, team2 = pair #here we filter out some domains, including pairs that have played already as well as pairs that have
        if (team_game_count[team1] < max_games
                and team_game_count[team2] < max_games ):

            valid_pairs.append(pair)
    random.shuffle(valid_pairs)
    db_print(valid_pairs)


    return valid_pairs



def causes_break(assignment,cur_week,team1,team2,var): #simply check if break is caused, returns which teams recieve a break

    if var.time_slot == '8:30' or var.time_slot == '9:30':
        assignment_items = list(assignment.items())  # itemize current assignments
        n = len(assignment.items()) - 1

        if var.time_slot == '8:30':
            while assignment_items[n][0].week == cur_week and n >= 0:  # go back to 6:30 games of current week
                n -= 1
            pair = []
            n += 1

            while assignment_items[n][0].time_slot == '6:30':  # check if teams also have a 6:30 game that week
                if (team1 in assignment_items[n][0].assigned_teams):
                    pair.append(team1)
                if (team2 in assignment_items[n][0].assigned_teams):
                    pair.append(team2)
                n += 1
            return pair
        elif var.time_slot == '9:30':
            while assignment_items[n][0].week == cur_week and n >= 0:  # go back to 6:30 games of current week
                n -= 1
            pair = []
            n += 1

            while assignment_items[n][0].time_slot != '8:30':  # check if teams also have a 6:30 game that week
                if (team1 in assignment_items[n][0].assigned_teams):
                    pair.append(team1)
                if (team2 in assignment_items[n][0].assigned_teams):
                    pair.append(team2)
                n += 1
            return pair


def uses_breaks():
    return ntimes % 2 == 1

def generate_unique_combinations(domain):
    teams1 = set(team for pair in domain for team in pair)
    unique_combos = list(combinations(teams1, 2))
    return unique_combos

#######################################################################################################################


def main():


    games = []
    for week in range(nweeks):
        for time in times:
            for field in range(nfields):
                games.append(Game(time, field, week))

    if games_in_a_week > 1:
        if len(times) > 2:
            constraints = [each_team_plays, no_conflicts, respects_break_scheduling, respects_alternating_times, plays_each_team]
        else:
            constraints = [each_team_plays, no_conflicts, respects_alternating_times,plays_each_team]
    else:
        constraints = [each_team_plays, no_conflicts,respects_alternating_times,plays_each_team]



        # Create the CSP instance
    csp = CSP(games, constraints)

    # Solve the CSP
    solution = recursive_backtracking({}, csp)

    if solution:
        db_print("Solution found:")
        print_state(solution)
        return 0

main()