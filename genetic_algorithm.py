import random
from deap import base, creator, tools, algorithms
from functools import cmp_to_key

def parse_time(time_str):
    try:
        h, m = map(int, time_str.split(':'))
        return h * 60 + m
    except (ValueError, AttributeError):
        return 0

def timeslot_to_numeric(timeslot_str):
    try:
        start_str, end_str = timeslot_str.split('-')
        return parse_time(start_str.strip()), parse_time(end_str.strip())
    except (ValueError, AttributeError):
        return 0, 0

def get_final_schedule(individual, required_lectures, constraints, schedulable_slots, days):
    """
    This function takes the best individual (a lecture sequence) and builds the final timetable.
    It's a deterministic scheduler based on a given sequence.
    """
    
    # 1. Create and sort all possible 1-hour slots
    all_slots = []
    for day in days:
        for timeslot_str in schedulable_slots:
            all_slots.append({'day': day, 'timeslot': timeslot_str})
    
    # Sort slots chronologically, which is critical for finding consecutive slots
    def compare_slots(s1, s2):
        day1_idx, day2_idx = days.index(s1['day']), days.index(s2['day'])
        if day1_idx != day2_idx:
            return day1_idx - day2_idx
        time1_start, _ = timeslot_to_numeric(s1['timeslot'])
        time2_start, _ = timeslot_to_numeric(s2['timeslot'])
        return time1_start - time2_start
    
    all_slots.sort(key=cmp_to_key(compare_slots))

    # 2. Pre-calculate which slots are consecutive for 2-hour labs
    consecutive_map = {}
    for i in range(len(all_slots) - 1):
        s1 = all_slots[i]
        s2 = all_slots[i+1]
        if s1['day'] == s2['day']:
            _, s1_end = timeslot_to_numeric(s1['timeslot'])
            s2_start, _ = timeslot_to_numeric(s2['timeslot'])
            if s1_end == s2_start:
                consecutive_map[i] = i + 1

    # 3. Schedule lectures based on the individual's sequence
    slot_occupied = [False] * len(all_slots)
    final_timetable = []
    
    for lecture_index in individual:
        lecture = required_lectures[lecture_index]
        duration = lecture.get('duration', 1)
        placed = False
        
        for i in range(len(all_slots)):
            if duration == 1 and not slot_occupied[i]:
                slot = all_slots[i]
                final_timetable.append({'subject_name': lecture['subject_name'], 'professor_name': lecture['professor_name'], **slot})
                slot_occupied[i] = True
                placed = True
                break
            
            elif duration == 2 and i in consecutive_map:
                j = consecutive_map[i]
                if not slot_occupied[i] and not slot_occupied[j]:
                    slot1 = all_slots[i]
                    slot2 = all_slots[j]
                    
                    # For a 2-hour lab, we add two entries to the timetable
                    final_timetable.append({'subject_name': lecture['subject_name'], 'professor_name': lecture['professor_name'], **slot1})
                    final_timetable.append({'subject_name': lecture['subject_name'], 'professor_name': lecture['professor_name'], **slot2})

                    slot_occupied[i] = True
                    slot_occupied[j] = True
                    placed = True
                    break
        
        if not placed:
            # This should not happen if the fitness function works correctly
            return None 
            
    return final_timetable


def evaluate(individual, required_lectures, constraints, schedulable_slots, days):
    """
    Fitness function. The individual is a sequence of lectures to place.
    The fitness is determined by how many lectures can be placed without violating hard constraints.
    """
    # This function now simulates the scheduling process to evaluate a sequence
    # It mirrors the logic in get_final_schedule but focuses on calculating a score
    
    all_slots = []
    for day in days:
        for timeslot_str in schedulable_slots:
            all_slots.append({'day': day, 'timeslot': timeslot_str})

    def compare_slots(s1, s2):
        day1_idx, day2_idx = days.index(s1['day']), days.index(s2['day'])
        if day1_idx != day2_idx:
            return day1_idx - day2_idx
        time1_start, _ = timeslot_to_numeric(s1['timeslot'])
        time2_start, _ = timeslot_to_numeric(s2['timeslot'])
        return time1_start - time2_start
    all_slots.sort(key=cmp_to_key(compare_slots))

    consecutive_map = {}
    for i in range(len(all_slots) - 1):
        s1, s2 = all_slots[i], all_slots[i+1]
        if s1['day'] == s2['day']:
            _, s1_end = timeslot_to_numeric(s1['timeslot'])
            s2_start, _ = timeslot_to_numeric(s2['timeslot'])
            if s1_end == s2_start:
                consecutive_map[i] = i + 1

    slot_occupied = [False] * len(all_slots)
    lectures_placed = 0
    penalty = 0

    for lecture_index in individual:
        lecture = required_lectures[lecture_index]
        duration = lecture.get('duration', 1)
        placed = False
        
        for i in range(len(all_slots)):
            # Check professor availability constraint
            def check_prof_constraint(lec, slt):
                for const in constraints:
                    if const['professor_name'] == lec['professor_name'] and const['day'] == slt['day']:
                        const_start, const_end = parse_time(const['start_time']), parse_time(const['end_time'])
                        slot_start, slot_end = timeslot_to_numeric(slt['timeslot'])
                        if max(slot_start, const_start) < min(slot_end, const_end):
                            return True # Professor is unavailable
                return False

            if duration == 1 and not slot_occupied[i]:
                if not check_prof_constraint(lecture, all_slots[i]):
                    slot_occupied[i] = True
                    placed = True
                    break
            
            elif duration == 2 and i in consecutive_map:
                j = consecutive_map[i]
                if not slot_occupied[i] and not slot_occupied[j]:
                    if not check_prof_constraint(lecture, all_slots[i]) and not check_prof_constraint(lecture, all_slots[j]):
                        slot_occupied[i] = True
                        slot_occupied[j] = True
                        placed = True
                        break

        if placed:
            lectures_placed += 1
        else:
            penalty += 10 # Add a penalty for each unplaced lecture

    score = lectures_placed * 10 - penalty * 100
    return (score,)


def run_genetic_algorithm(required_lectures, constraints, schedulable_slots, days):
    # Forcefully delete any existing DEAP types
    if hasattr(creator, "FitnessMax"): del creator.FitnessMax
    if hasattr(creator, "Individual"): del creator.Individual

    creator.create("FitnessMax", base.Fitness, weights=(1.0,))
    creator.create("Individual", list, fitness=creator.FitnessMax)

    toolbox = base.Toolbox()
    
    # An individual is a PERMUTATION of lecture indices
    lecture_indices = list(range(len(required_lectures)))
    toolbox.register("indices", random.sample, lecture_indices, len(lecture_indices))
    toolbox.register("individual", tools.initIterate, creator.Individual, toolbox.indices)
    toolbox.register("population", tools.initRepeat, list, toolbox.individual)

    toolbox.register("evaluate", evaluate, required_lectures=required_lectures, constraints=constraints, schedulable_slots=schedulable_slots, days=days)
    
    # Crossover and mutation operators for permutations
    toolbox.register("mate", tools.cxOrdered)
    toolbox.register("mutate", tools.mutShuffleIndexes, indpb=0.05)
    toolbox.register("select", tools.selTournament, tournsize=3)

    population = toolbox.population(n=200)
    hof = tools.HallOfFame(1)
    
    algorithms.eaSimple(population, toolbox, cxpb=0.7, mutpb=0.2, ngen=150, halloffame=hof, verbose=False)
    
    best_individual = hof[0]
    
    # Check if the best solution is valid (all lectures placed, no hard constraints violated)
    if best_individual.fitness.values[0] < len(required_lectures) * 10:
        return None

    # Use the best sequence to build the final, clean timetable
    final_timetable = get_final_schedule(best_individual, required_lectures, constraints, schedulable_slots, days)

    return final_timetable