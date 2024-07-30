import os
import subprocess
import time
import re
import json
def parse_game_count(lines):
    game_count_str = lines[1].strip()
    return json.loads(game_count_str.replace("'", '"'))

def parse_break_count(lines):
    break_count_str = lines[3].strip()
    return json.loads(break_count_str.replace("'", '"'))

def test_game_count(game_count):
    first_key = next(iter(game_count))
    ngames = game_count[first_key]
    for team in game_count:
        if game_count[team] != ngames:
            return 1
    return 0

def test_break_count(break_count):
    first_key = next(iter(break_count))
    ngames = break_count[first_key]
    for team in break_count:
        if break_count[team] != ngames:
            return 1
    return 0


def test_team_pair_matrix(matrix):
    non_diagonal_values = []

    i = 0
    for row in matrix:
        j = 0
        for item in row:
            if i != j:
                non_diagonal_values.append(int(item))
            elif i != 0: #dont play selves
              return 1
            j += 1
        i += 1

    min_value = min(non_diagonal_values)
    max_value = max(non_diagonal_values)

    if (max_value - min_value) < 2:
        return 0
    return 1

def test_balanced_times(team_times):
    min_time = 999
    max_time = -999
    for team in team_times:
        for time in team_times[team]:
            if team_times[team][time] > max_time:
                max_time = team_times[team][time]
            if team_times[team][time] < min_time:
                min_time = team_times[team][time]
    print(min_time)
    print(max_time)



def parse_team_play_count_matrix(lines, nteams):

    # Extract headers
    headers = lines[7].split()[1:]  # Skip the first header
    headers = [header.strip() for header in headers]  # Remove extra whitespace

    matrix = {header: {} for header in headers}

    # Process each line to fill the matrix
    for line in lines[7:7+(nteams)]:
        parts = line.split()

        # Debug print statements

        if len(parts) < nteams + 1:
            continue

        team = parts[0].strip()
        for i, header in enumerate(headers):
            matrix[header][team] = int(parts[i + 1].strip())
    return matrix


def parse_team_times(lines, nteams, ntimes):
    team_times = {}
    index = 7 + nteams  # Adjust the starting index if needed

    for _ in range(nteams):
        # Get the team name
        team_name = lines[index].strip().rstrip(':')
        index += 1

        # Initialize dictionary for storing time counts
        times = {}

        for _ in range(ntimes):
            time_line = lines[index].strip()

            # Skip empty lines
            if not time_line:
                break

            # Split the line into time and count
            parts = time_line.split(':')
            if len(parts) == 3:
                time = parts[0] + ":" + parts[1]
                try:
                    count = int(parts[-1])
                except ValueError:
                    count = None  # Handle unexpected formats or missing values
                times[time] = count
                index += 1


        team_times[team_name] = times
        index += 1  # Skip the blank line after each team's time count

    return team_times



def parse_schedule(lines):
    # Find the index where the schedule starts
    schedule_start = None
    for i, line in enumerate(lines):
        if line.strip().startswith("Week"):
            schedule_start = i
            break

    if schedule_start is None:
        return {}

    # Extract schedule lines
    schedule_lines = lines[schedule_start:]

    # Use regex to extract week, time, and teams
    pattern = r"Week (\d+), Time (\d+:\d+), Field \d+: \(([^,]+), ([^)]+)\)"
    matches = re.findall(pattern, "\n".join(schedule_lines))

    schedule = {}
    for week, time, team1, team2 in matches:
        week_time = f"Week {week} Time {time}"
        if week_time not in schedule:
            schedule[week_time] = []
        schedule[week_time].append((team1, team2))

    return schedule

def run_program_with_params(nteams, ntimes, nfields, nweeks, games_per_week):
    max_attempts = 20
    attempt = 0

    # Construct the filename based on parameters
    result_filename = f"test_results/{nteams}_{ntimes}_{nfields}_{nweeks}_{games_per_week}_results.txt"

    while attempt < max_attempts:
        try:
            result = subprocess.run(
                ["python3", "main.py", str(nteams), str(ntimes), str(nfields), str(nweeks), str(games_per_week)],
                capture_output=True,
                text=True,
                timeout=8  # Timeout in seconds
            )

            # Write the output to the file
            with open(result_filename, "w") as file:
                file.write(result.stdout)

            if result.returncode == 0:
                output = result.stdout.strip()
                if output == "No solution found.":
                    print(f"Test case failed (No solution found): nteams={nteams}, ntimes={ntimes}, nfields={nfields}, nweeks={nweeks}, games_per_week={games_per_week}")
                    return False

                print("Output written to:", result_filename)

                return  True



            else:
                print(f"Test case failed (exit code {result.returncode}): nteams={nteams}, ntimes={ntimes}, nfields={nfields}, nweeks={nweeks}, games_per_week={games_per_week}")

        except subprocess.TimeoutExpired:
            print(f"Timeout occurred for test case: nteams={nteams}, ntimes={ntimes}, nfields={nfields}, nweeks={nweeks}, games_per_week={games_per_week}")

        except Exception as e:
            print(f"Error occurred for test case: nteams={nteams}, ntimes={ntimes}, nfields={nfields}, nweeks={nweeks}, games_per_week={games_per_week}")
            print(f"Error details: {str(e)}")

        attempt += 1
        if attempt < max_attempts:
            continue
        print(f"Test case failed after {max_attempts} attempts: nteams={nteams}, ntimes={ntimes}, nfields={nfields}, nweeks={nweeks}, games_per_week={games_per_week}")
        return False

    print(f"Test case failed after {max_attempts} attempts: nteams={nteams}, ntimes={ntimes}, nfields={nfields}, nweeks={nweeks}, games_per_week={games_per_week}")
    return False


def parse_and_test(filename):
    with open(filename, "r") as file:
        lines = file.readlines()

    # Parse each section based on the file structure
    game_count = parse_game_count(lines)
    break_count = parse_break_count(lines)
    nteams = len(lines[7].split()) - 1
    team_play_count_matrix = parse_team_play_count_matrix(lines,nteams)
    team_times = parse_team_times(lines, nteams, 20)  # Adjust based on your file
    schedule = parse_schedule(lines)

    print("Checkng equal games per team...")
    if test_game_count(game_count) == 1:
        print("Fail!")
        return 1

    print("Checking equal breaks per team...")
    if test_break_count(break_count) == 1:
        print("Fail!")
        return 1

    print("Checking team-pair matrix (difference of < 2 except for self)...")
    if test_team_pair_matrix(team_play_count_matrix) == 1:
        print("Fail!")
        return 1

    print("Checking time balancing... ")
    if test_balanced_times(team_times) == 1:
        print("Fail!")
        return 1
    # Print or use the parsed data
    #print("Game Count:", game_count) #check equal games
    #print("Break Count:", break_count) #check equal breaks
    #print("Team Play Count Matrix:", team_play_count_matrix) # check valid play count
    #print("Team Times:", team_times) # check balanced team times
   #print("Schedule:", schedule)

    print("Success.")



    return 0



def process_test_cases(filename):
    with open(filename, 'r') as file:
        for line in file:
            # Assuming each line in the file has the format: nteams ntimes nfields nweeks games_per_week
            params = line.strip().split()
            if len(params) == 5:
                nteams, ntimes, nfields, nweeks, games_per_week = map(int, params)
                run_program_with_params(nteams, ntimes, nfields, nweeks, games_per_week)
            else:
                print(f"Invalid format in line: {line}")

def main():
    test_cases_file = "test_cases.txt"
    process_test_cases(test_cases_file)
    success_tests = []
    failed_tests = []

    with open(test_cases_file, "r") as f:
        lines = f.readlines()

    for line in lines:
        line = line.strip()
        if line and line.replace(" ", "").isdigit():  # Check if the line contains only numeric characters and spaces
            params = list(map(int, line.split()))
            if len(params) == 5:
                nteams, ntimes, nfields, nweeks, games_per_week = params
                result_filename = f"test_results/{nteams}_{ntimes}_{nfields}_{nweeks}_{games_per_week}_results.txt"
                if os.path.exists(result_filename):
                    print(f"Parsing and testing results from: {result_filename}")

                    if parse_and_test(result_filename) == 0:
                        success_tests.append(params)
                    else:
                        failed_tests.append(params)
                else:
                    print(f"Results file not found: {result_filename}")
                    failed_tests.append(params)

    print("\nSummary:")
    print("Succeeded Tests:")
    for test in success_tests:
        print(test)

    print("Failed Tests:")
    for test in failed_tests:
        print(test)


if __name__ == "__main__":
    main()
