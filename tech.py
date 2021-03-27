"""
our initial naive solution to detecting tech patterns
is finding grouping of foot orderings, such as:

    Left, Up, Right, Up

Which would be a crossover.

There may be cases where charts don't properly cross over, or
patterns that look like footswitches don't work in context.

This is a heuristic measure for now. In the future we can make
it smarter.
"""

# Count all crosses, and divide by 2. An unresolved XO counts as half lol
CROSSOVERS = {
    "LDR",
    "LUR",
    "RDL",
    "RUL",
}

FOOTSWITCHES = {
    "LUUR",
    "LUUD",
    "LDDR",
    "LDDU",
    "RUUL",
    "RUUD",
    "RDDL",
    "RDDU",
    "UDDR",
    "UDDL",
    "UDDU",
    "DUUL",
    "DUUR",
    "DUUD",
}

NOTE_TYPES = {"1", "2", "4"}
ARROW_DIRECTIONS = "LDUR"


# TODO: Use this to parse through measures by subdivision, and denote
#  "foot resets" with longer gaps, rather than marking a XO or FS over
#  a long gap
# def chart_generator(measure_list):
#     for measure in measure_list:
#         for subdivision_number, subdivision in enumerate(measure):
#             yield subdivision_number, len(measure), subdivision

def generate_arrow_list(measure_list):
    arrow_list = []
    current_arrow = 0
    for measure in measure_list:
        for subdivision in measure:
            arrow_count = 0
            for slot in subdivision:
                if slot in NOTE_TYPES:
                    current_arrow = slot
                    arrow_count += 1
            if arrow_count == 1:
                direction = ARROW_DIRECTIONS[subdivision.index(current_arrow)]
                arrow_list.append(direction)
            elif arrow_count == 2:
                arrow_list.append("J")
            elif arrow_count >= 3:
                arrow_list.append("H")
    return "".join(arrow_list)


def detect_crossovers_and_footswitches(arrow_list):
    crossover_count = footswicth_count = 0

    # detect patterns in the last few notes without any overflow issues
    arrow_list += "XXXXX"

    for i in range(len(arrow_list)):
        if arrow_list[i:i + 3] in CROSSOVERS:
            crossover_count += 1
        elif arrow_list[i:i + 4] in FOOTSWITCHES:
            footswicth_count += 1
    return int(crossover_count / 2), footswicth_count


def detect_tech_patterns(measure_list):
    arrow_list = generate_arrow_list(measure_list)
    crossover_count, footswitch_count = detect_crossovers_and_footswitches(arrow_list)
    # TODO: detect jacks, brackets, and side-switches
    return crossover_count, footswitch_count
