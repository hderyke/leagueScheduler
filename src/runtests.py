import os
import subprocess
import re
import json
import sys
from collections import Counter
import shutil


n_stored_schedules = 3
n_iterations = 10000

def parse_game_count(lines):
    game_count_str = lines[2].strip()
    return json.loads(game_count_str.replace("'", '"'))


def parse_break_count(lines):
    break_count_str = lines[4].strip()
    return json.loads(break_count_str.replace("'", '"'))


def parse_team_play_count_matrix(lines, nteams):

    # Extract headers
    headers = lines[8].split()[1:]  # Skip the first header
    headers = [header.strip() for header in headers]  # Remove extra whitespace
    matrix = {header: {} for header in headers}

    # Process each line to fill the matrix
    for line in lines[8:8+(nteams)]:
        parts = line.split()
        if len(parts) < nteams + 1:
            continue

        team = parts[0].strip()
        for i, header in enumerate(headers):
            matrix[header][team] = int(parts[i + 1].strip())
    return matrix


def parse_team_times(lines, nteams, ntimes):
    team_times = {}
    index = 9 + nteams  # Adjust the starting index if needed

    for _ in range(nteams):
        # Get the team name
        team_name = lines[index].strip().rstrip(':')
        index += 1
        # dictionary for storing time counts
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
        index += 1

    return team_times


def test_game_count(game_count):
    first_key = next(iter(game_count))
    ngames = game_count[first_key]
    for team in game_count:
        if game_count[team] != ngames:
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



def test_breaks(scorecard,break_count,nteams,ntimes,games_per_week):
    if games_per_week == 1:
        return [5,5]

    break_counts = list(break_count.values())
    # Get the mode value in break_counts list
    break_counter = Counter(break_counts)
    mode_value, mode_count = break_counter.most_common(1)[0]
    mode_count = int(mode_count)

    scorecard.append(5 - (5 * (1- mode_count/nteams)))

    break_range = max(break_counts) - min(break_counts)

    if break_range > 5:
        break_range = 5
    scorecard.append(5 - break_range)

    return scorecard


def test_time_distribution(scorecard, team_times, ntimes, games_per_week):
    nteams = len(team_times)
    nflat = 0
    all_times = []

    for team, times in team_times.items():
        # Check if the distribution is flat for this team
        time_counts = list(times.values())
        if max(time_counts) == min(time_counts):
            nflat += 1
        # Collect all time counts for overall range calculation
        all_times.extend(time_counts)

    # Adjust the score based on the number of flat distributions
    scorecard.append(5 * nflat / nteams)
    # Calculate the range of the whole time distribution
    time_range = max(all_times) - min(all_times)
    if time_range > 5:
        time_range = 5

    # Adjust the score based on the time range
    scorecard.append(5 - time_range)

    print(scorecard)
    return scorecard


def parse_and_test(filename,params):
    nteams, ntimes, nfields, nweeks, games_per_week = params
    score = 20
    scorecard = []
    with open(filename, "r") as file:
        lines = file.readlines()
    # Parse each section based on the file structure
    game_count = parse_game_count(lines)
    break_count = parse_break_count(lines)
    nteams = len(lines[8].split()) - 1
    team_play_count_matrix = parse_team_play_count_matrix(lines,nteams)
    team_times = parse_team_times(lines, nteams, 20)  # Adjust based on your file

    print("Checking equal games per team...")
    if test_game_count(game_count) == 1:
        print("Fail!")
        return -1

    print("Checking team-pair matrix (difference of < 2 except for self)...")
    if test_team_pair_matrix(team_play_count_matrix) == 1:
        print("Fail!")
        return -1
    print("Calculating quality points...")
    scorecard = test_breaks(scorecard,break_count,nteams,ntimes,games_per_week)
    scorecard = test_time_distribution(scorecard,team_times,ntimes,games_per_week)

    return scorecard


def propagate_scores(directory_path, param_digits, new_score, insertion_index, filename):
    # Shift existing scores down to make room for the new score
    for j in range(n_stored_schedules - 1, insertion_index, -1):
        old_file = os.path.join(directory_path, f"{param_digits}-{j}.txt")
        new_file = os.path.join(directory_path, f"{param_digits}-{j + 1}.txt")
        if os.path.exists(old_file):
            shutil.move(old_file, new_file)

    # Save the new score in the correct file
    new_file_path = os.path.join(directory_path, f"{param_digits}-{insertion_index + 1}.txt")
    shutil.copy2(filename, new_file_path)


def update_database(score, filename):
    param_digits = re.search(r'(\d+(_\d+)*)', filename).group(0)

    # Define the directory path
    directory_path = "../schedule_database/" + param_digits
    # Create the directory if it doesn't exist
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)

    # Check existing score files and manage indices
    i = 0
    while i < n_stored_schedules:
        file_path = os.path.join(directory_path, f"{param_digits}-{i + 1}.txt")
        if os.path.exists(file_path):
            # Read the existing score from the file
            with open(file_path, 'r') as file:
                lines = file.readlines()
                # Assuming score is on the 6th line after "Total: "
                for line in lines:
                    if line.startswith("Total: "):
                        existing_score = float(line.strip().split("Total: ")[1])
                        break
            # Compare scores and update if necessary
            if score > existing_score:
                # Propagate scores and insert the new score
                propagate_scores(directory_path, param_digits, score, i,filename)
                break
            i += 1
        else:
            # Save the new score in the current file
            new_file_path = os.path.join(directory_path, f"{param_digits}-{i + 1}.txt")
            shutil.copy2(filename, new_file_path)
            break

    # If all slots are occupied and the new score is higher than the lowest
    if i == n_stored_schedules:
        # Handle the case where the new score is better than the lowest stored score
        lowest_file = os.path.join(directory_path, f"{param_digits}-{n_stored_schedules}.txt")
        with open(lowest_file, 'r') as file:
            lines = file.readlines()
            for line in lines:
                if line.startswith("Total: "):
                    lowest_score = float(line.strip().split("Total: ")[1])
                    break
        if score > lowest_score:
            # Remove the lowest score file and insert the new score
            os.remove(lowest_file)
            propagate_scores(directory_path, param_digits, score, 0,filename)


def run_program_with_params(nteams, ntimes, nfields, nweeks, games_per_week):
    max_attempts = 20
    attempt = 0

    # Construct the filename based on parameters
    result_filename = f"../{nteams}_{ntimes}_{nfields}_{nweeks}_{games_per_week}_results.txt"

    while attempt < max_attempts:
        try:
            result = subprocess.run(
                ["python3", "generator.py", str(nteams), str(ntimes), str(nfields), str(nweeks), str(games_per_week)],
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
                print("Schedule built, output written to:", result_filename)
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


def issue_score(filename, scorecard):
    # Prepare the content to prepend
    score_rows = ["Break distribution: " + str(scorecard[0]), "Break distribution range: "+ str(scorecard[1]), "Time slot distribution: "+ str(scorecard[2]), "Time slot distribution range: "+ str(scorecard[-1]),"","Total: "+str(sum(scorecard))]
    prepend_content = "\n".join(score_rows) + "\n------------------------------\n"

    # Read existing content from the file
    if os.path.exists(filename):
        with open(filename, 'r') as file:
            existing_content = file.read()
    else:
        existing_content = ""

    # Write the new content (prepend_content + existing_content) to the file
    with open(filename, 'w') as file:
        file.write("---------TEST SCORES--------\n"+ prepend_content + existing_content)

    return 0


def main():
    result_filename = None
    single_mode = False
    if len(sys.argv) == 3 and sys.argv[1] == "-f": #if using a list of cases
        test_cases_file = "../"+sys.argv[-1]
        if not os.path.exists(test_cases_file):
            print("Error: File '"+test_cases_file+"' could not be found. ")
            exit(0)
    elif len(sys.argv) == 2: #if testing one case file
        single_mode = True
        result = True
        result_filename = "../"+sys.argv[-1]
        if not os.path.exists(result_filename):
            print("Error: File '"+result_filename+"' could not be found. ")
            exit(0)
    elif len(sys.argv) == 6: #if inputting prarmeters for single case
        single_mode = True # for sunning like main but with tests at the end
        try:
            nteams = int(sys.argv[1])
            ntimes = int(sys.argv[2])
            nfields = int(sys.argv[3])
            nweeks = int(sys.argv[4])
            games_per_week = int(sys.argv[5])
        except:
            print("Error: Please enter numbers (ex. 'python3 runtests.py 4 2 2 2 2')")
            exit(0)
    elif len(sys.argv) == 1: #default case
        print("No arguments specified, using default file")
        test_cases_file = "../test_cases.txt"
    else:
        print("Usages:")
        print("python3 runtests.py (will run cases in test_cases.txt)")
        print("python3 runtests.py -f <list_of_test_cases_file>")
        print("python3 runtests.py <generated schedule file>")
        print("python3 runtests.py <nteams> <ntimes> <nfields> <nweeks> <games_per_week>")
        exit(0)

    #otherwise just use the given schedule file and append
    if single_mode:
        if result_filename == None:
            params = nteams, ntimes, nfields, nweeks, games_per_week
            result = run_program_with_params(nteams, ntimes, nfields, nweeks, games_per_week)
            result_filename = f"../{nteams}_{ntimes}_{nfields}_{nweeks}_{games_per_week}_results.txt"
        else:
            try:
                with open(result_filename, 'r') as file:
                    first_line = file.readline().strip()  # Read the first line and strip any surrounding whitespace
                    if first_line == '---------TEST SCORES--------':
                        print("Error: This schedule has already been tested!")
                        return 0
                    params = list(map(int, first_line.split()))  # Split the line by spaces and convert each to an integer
            except:
                print("Error: File could not be read")
                return 0

        if result and os.path.exists(result_filename):
            print(f"Parsing and testing results from: {result_filename}")
            try:
                scorecard = parse_and_test(result_filename, params)
            except:
                scorecard = None
            if scorecard != None:
                issue_score(result_filename, scorecard)
                with open(result_filename, 'r') as file:
                    contents = file.read()
                    print(contents)
                    if len(sys.argv) != 2:
                        os.remove(result_filename)
            else:
                print("Error: File could not be read.")
        return 0



    with open(test_cases_file, "r") as f:
        lines = f.readlines()
    iteration = 0
    while iteration < n_iterations:
        for line in lines:
            line = line.strip()
            if line and line.replace(" ", "").isdigit():  # Check if the line contains only numeric characters and spaces
                params = list(map(int, line.split()))
                if len(params) == 5:
                    nteams, ntimes, nfields, nweeks, games_per_week = params
                    result = run_program_with_params(nteams, ntimes, nfields, nweeks, games_per_week)
                    result_filename = f"../{nteams}_{ntimes}_{nfields}_{nweeks}_{games_per_week}_results.txt"
                    if result and os.path.exists(result_filename):
                        print(f"Parsing and testing results from: {result_filename}")
                        try:
                            scorecard = parse_and_test(result_filename, params)
                            if scorecard!= None:
                                issue_score(result_filename, scorecard)
                                score = sum(scorecard)
                            # send to the database for updating
                                update_database(score, result_filename)
                        except:
                            scorecard = None
                        os.remove(result_filename)
                    else:
                        print(f"Results file not found: {result_filename}")
            else:
                print("Error reading line.")
                continue
        iteration += 1
    return 0


if __name__ == "__main__":
    main()
