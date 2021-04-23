from step_parser.constants import NOTE_TYPES


ARROW_DIRECTIONS = "LDUR"


def generate_arrow_list(measure_list):
    """
    For a list of measures, return a string denoting
    consecutive directions of each step, like:

        RUDURLRUJDRDUDRL...

    LDUR = Left Down Up Right
    J = Jump (direction not specified)
    H = Hand/Quad (direction not specified)
    """
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


def detect_tech_patterns(measure_list, invalid_crossover_threshold=9):
    """
    This solution is does not handle:
        * holds or rolls: the initial hold note will count as a normal note
        * intentional double-steps: they will be counted as footswitches or jacks

    Crossovers              - group of left or right arrows you hit
                              with the opposite foot
    Footswitches            - 2 of the same note in a row
    Jacks                   - 3+ of the same note in a row
    Crossover footswitches  - footswitches that happen while crossed over
    Invalid crossovers      - Crossovers that last more than some threshold
                              number of notes

    Crossover Footswitches also count as both crossovers and footswitches
    """
    arrow_list = generate_arrow_list(measure_list)

    crossovers = 0
    footswitches = 0
    jacks = 0
    crossover_footswitches = 0

    # If you are crossed over for too many steps, revert your
    # footing and count an invalid crossover
    invalid_crossovers = 0

    right_foot = True
    left_foot = False

    # * jumps and hands reset foot positioning. Brackets + crossovers
    #   aren't accounted for, but are very rare.
    # * crossovers can only occur in groups that have both left and right
    #   arrows, with rare exceptions
    arrow_groups = [
        group for group in
        arrow_list.replace("H", "J").split("J")
        if len(group) >= 3
           and "L" in group
           and "R" in group
    ]

    for group in arrow_groups:
        next_side_arrows = {
            "L": group.index("L"),
            "R": group.index("R"),
        }
        next_side_arrow = (
            right_foot
            if next_side_arrows["R"] < next_side_arrows["L"]
            else left_foot
        )
        steps_before_next_side_arrow = min(next_side_arrows.values())
        if steps_before_next_side_arrow % 2 == 0:
            starting_foot = next_side_arrow
        else:
            starting_foot = not next_side_arrow

        active_foot = starting_foot
        previous_arrow = None
        crossed_over = False
        in_footswitch = False
        in_jack = False
        crossed_over_length = 0

        for arrow in group:
            # FS/Jack detection
            if arrow == previous_arrow:
                if not in_footswitch:
                    in_footswitch = True
                else:
                    in_jack = True
            elif in_jack:
                jacks += 1
                in_footswitch = False
                in_jack = False
            elif in_footswitch:
                footswitches += 1
                in_footswitch = False
                in_jack = False

            # Crossover detection
            if (arrow == "L" and active_foot == right_foot) \
                    or (arrow == "R" and active_foot == left_foot):
                crossed_over = True

            if crossed_over and (
                    (arrow == "L" and active_foot == left_foot)
                    or (arrow == "R" and active_foot == right_foot)):
                crossovers += 1
                crossed_over = False
                crossed_over_length = 0
                if arrow == previous_arrow:
                    crossover_footswitches += 1

            if crossed_over:
                crossed_over_length += 1
                if crossed_over_length >= invalid_crossover_threshold:
                    invalid_crossovers += 1
                    crossed_over = False
                    active_foot = not active_foot
                    crossed_over_length = 0

            active_foot = not active_foot
            previous_arrow = arrow

    return (
        crossovers,
        footswitches,
        crossover_footswitches,
        jacks,
        invalid_crossovers
    )


def detect_jumps_hands_quads(measure_list):
    """
    Note:
        this does not account for holds/rolls yet, so songs like
        Bend Your Mind will produce wildly incorrect results.
    :param measure_list:
        List of measures, with list of subdivisions of notes. eg:
        [['0001', '1000', '0100', '0010'], ['0100', '0000', '1001', '0000'], ...]
    :return:
        (jumps, hands, quads, mines, holds, rolls)
    """
    jumps = hands = quads = mines = holds = rolls = 0
    for measure in measure_list:
        for subdivision in measure:
            arrow_counter = 0
            # indexing each possible step per row
            for i in range(0, 4):
                if subdivision[i] in NOTE_TYPES:
                    arrow_counter += 1
                if subdivision[i].lower() == "m":
                    mines += 1
                if subdivision[i].lower() == "2":
                    holds += 1
                if subdivision[i].lower() == "4":
                    rolls += 1
            if arrow_counter == 2:
                jumps += 1
            elif arrow_counter == 3:
                hands += 1
            elif arrow_counter == 4:
                quads += 1

    return (
        jumps,
        hands,
        quads,
        mines,
        holds,
        rolls,
    )
