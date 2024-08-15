# look up param combo and get games in order of score
import os
import re
import signal
import sys

def signal_handler(sig, frame):
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

# give ability to choose a schedule and
def main():

    old_times = ['6:30','7:30','8:30','9:30'] # default times for the problem to be replaced

    while True:
        try:
            params = input("Enter parameters: ")
            number_strings = params.split()
            # Convert the list of strings to a list of integers
            numbers = [int(num) for num in number_strings]
            if len(numbers) != 5:
                print(
                    "Error: please enter schedule parameters as such: {nteams} {ntimes} {nfields} {nweeks} {games_per_week}")
                continue
        except ValueError:
            print(
                "Error: please enter schedule parameters as such: {nteams} {ntimes} {nfields} {nweeks} {games_per_week}")
            continue
        except KeyboardInterrupt:
            sys.exit(0)
        break

    nteams = numbers[0]
    ntimes = numbers[1]
    nfields = numbers[2]
    nweeks = numbers[3]
    games_per_week = numbers[-1]
    teams = []
    slots = []


    #generate all database entries in point order
    dir = "../schedule_database/"+str(nteams)+"_"+str(ntimes)+"_"+str(nfields)+"_"+str(nweeks)+"_"+str(games_per_week)

    if os.path.exists(dir):
        print("Paste team names on seperate lines: ")
        for i in range(nteams):
            teams.append(input())

        # enter your time slots
        print("Paste time slots on separate lines: ")
        for i in range(ntimes):
            slots.append(input())

        for filename in os.listdir(dir):
            # Construct full file path
            file_path = os.path.join(dir, filename)

            with open(file_path, 'r') as file:
                buffer = file.read()

                # Replace every instance of "Team_{i}" with the corresponding replacement
            for i in range(1, nteams + 1):
                old_text = f"Team_{i}"
                # Use regular expressions to ensure we match whole words only
                pattern = rf'\b{old_text}\b'
                new_text = teams[i - 1]  # Access the corresponding team name from the list
                buffer = re.sub(pattern, new_text, buffer)

            for i in range(len(slots)):
                old_time = old_times[i]
                new_time = slots[i]
                buffer = buffer.replace(old_time, new_time)
            print("---------------------------------------------------------------------------------------------------")
            print(buffer)

    else:
        print("No file in the database yet. Start generating and testing with runtests?")


if __name__ == "__main__":
    main()
